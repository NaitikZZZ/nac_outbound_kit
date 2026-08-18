"""Measure how much of the Xoxoday ICP actually exists inside Apollo.

For every canonical title family in icp_titles.py this queries Apollo's people search
and reads `total_entries` -- the size of Apollo's own universe for that title -- then
divides by the modelled TAM from tam_sam_som.py to get real coverage.

Pass 0 audits the taxonomy's variant strings against Apollo's title matching, which
dilutes long phrases, and drops the ones that provably over-match. Pass 1 then measures:
  global x 3 size tiers      60 x 3 = 180 cells
  verified-email subset      60     =  60 cells  (--verified)
  per region at 200+         60 x 9 = 540 cells  (--regions)

Every cell is cached to outputs/_apollo_counts_cache.json keyed by its query, so an
interrupted run resumes exactly where it stopped and costs nothing to re-invoke.

Usage:
  python3 scripts/apollo_title_counts.py --regions --verified

The key is read from APOLLO_API_KEY or .env and never printed. Search only reads counts:
no enrichment, no export credits consumed.

Caveat: total_entries counts records Apollo HAS, not records you can export. Paging is
capped around 50k, but we only ever read the count, so the page cap does not bite.
"""
import argparse
import concurrent.futures
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from icp_titles import FAMILIES  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "outputs")
CACHE = os.path.join(OUT, "_apollo_counts_cache.json")

# mixed_people/search is deprecated for API callers (422). api_search is the replacement
# and returns total_entries at the top level rather than nested under `pagination`.
URL = "https://api.apollo.io/api/v1/mixed_people/api_search"

# Apollo's own employee-range buckets, mapped to our size tiers.
TIER_RANGES = {
    "200+": ["201,500", "501,1000", "1001,2000", "2001,5000", "5001,10000", "10001,1000000"],
    "1000+": ["1001,2000", "2001,5000", "5001,10000", "10001,1000000"],
    "5000+": ["5001,10000", "10001,1000000"],
}

# person_locations strings Apollo recognises, grouped to match the model's regions.
REGION_LOCATIONS = {
    "United States": ["United States"],
    "Canada": ["Canada"],
    "UK & Ireland": ["United Kingdom", "Ireland"],
    "DACH / Benelux / France": ["Germany", "Austria", "Switzerland", "Netherlands",
                                "Belgium", "France"],
    "Nordics": ["Sweden", "Denmark", "Norway", "Finland"],
    "India": ["India"],
    "SEA": ["Singapore", "Malaysia", "Thailand", "Indonesia", "Philippines", "Vietnam"],
    "Middle East": ["United Arab Emirates", "Saudi Arabia", "Qatar", "Israel"],
    "Australia & NZ": ["Australia", "New Zealand"],
    "S. & E. Europe": ["Spain", "Italy", "Poland", "Portugal", "Greece",
                       "Czechia", "Romania"],
    "LatAm": ["Brazil", "Mexico", "Argentina", "Colombia", "Chile"],
    "Africa": ["South Africa", "Nigeria", "Kenya", "Egypt"],
    "China": ["China"],
    "Japan": ["Japan"],
    "South Korea": ["South Korea"],
}

# Apollo advertises 200 req/min, 6000/hr, 50k/day in its rate-limit headers, but 8
# workers drew steady 429s in practice, so the real search ceiling is lower than the
# header claims. 5 workers with a longer retry ladder still beats sequential ~5x.
WORKERS = 5
MAX_RETRY = 6
# Even at 5 workers Apollo returned 429s, because concurrent bursts trip its per-minute
# counter regardless of average rate. A global minimum spacing between request starts
# keeps the burst rate itself under the ceiling: 0.4s => 150 starts/min.
MIN_SPACING = 0.4
_spacer = threading.Lock()
_last_start = [0.0]


def _pace():
    with _spacer:
        wait = MIN_SPACING - (time.monotonic() - _last_start[0])
        if wait > 0:
            time.sleep(wait)
        _last_start[0] = time.monotonic()


def load_cache():
    if os.path.exists(CACHE):
        with open(CACHE) as f:
            return json.load(f)
    return {}


def save_cache(c):
    with open(CACHE, "w") as f:
        json.dump(c, f)


def query(api_key, titles, ranges=None, locations=None, verified_only=False):
    body = {"person_titles": titles, "page": 1, "per_page": 1}
    if ranges:
        body["organization_num_employees_ranges"] = ranges
    if locations:
        body["person_locations"] = locations
    if verified_only:
        body["contact_email_status"] = ["verified"]
    data = json.dumps(body).encode()
    req = urllib.request.Request(URL, data=data, method="POST", headers={
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "accept": "application/json",
        "x-api-key": api_key,
    })
    for attempt in range(MAX_RETRY):
        try:
            _pace()
            with urllib.request.urlopen(req, timeout=90) as r:
                payload = json.load(r)
            if payload.get("total_entries") is not None:
                return payload["total_entries"]
            return (payload.get("pagination") or {}).get("total_entries")
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < MAX_RETRY - 1:
                wait = 5 * (attempt + 1)
                print(f"    HTTP {e.code}, backing off {wait}s", flush=True)
                time.sleep(wait)
                continue
            # Surface the body -- Apollo puts plan/permission problems there.
            detail = e.read().decode(errors="replace")[:300]
            raise RuntimeError(f"Apollo HTTP {e.code}: {detail}") from None
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < MAX_RETRY - 1:
                time.sleep(5 * (attempt + 1))
                continue
            raise RuntimeError(f"Apollo unreachable: {e}") from None
    return None


def fetch_all(api_key, jobs, cache, label):
    """Resolve a batch of (cache_key, kwargs) jobs concurrently into the cache.

    Already-cached keys are skipped, which is what makes the whole run resumable after
    an interrupt. Failures are recorded as None rather than aborting the batch.
    """
    # A cell that exhausted its retries is stored as None. Treat that as unfetched so a
    # re-run repairs it, rather than caching the failure forever.
    todo = [(k, kw) for k, kw in jobs if cache.get(k) is None]
    if not todo:
        print(f"  {label}: all {len(jobs)} cells already cached")
        return
    print(f"  {label}: {len(todo)} to fetch ({len(jobs) - len(todo)} cached)", flush=True)
    lock = threading.Lock()
    done = [0]

    def work(item):
        k, kw = item
        try:
            val = query(api_key, **kw)
        except RuntimeError as e:
            print(f"    FAIL {k}: {e}", flush=True)
            val = None
        with lock:
            cache[k] = val
            done[0] += 1
            if done[0] % 50 == 0:
                save_cache(cache)
                print(f"    {done[0]}/{len(todo)}", flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        list(ex.map(work, todo))
    save_cache(cache)


STOPWORDS = {"of", "and", "&", "the", "for", "in", "a", "to"}


def content_words(v):
    return [w for w in v.split() if w not in STOPWORDS and len(w) > 1]


def audit_variants(cached):
    """Drop variants that Apollo dilutes into a shorter, commoner phrase.

    Apollo's title matching degrades badly on phrases: "people operations" returns
    1,012,109 records against 241,582 for "people" alone, because it also matches bare
    "operations". Any title string containing a phrase must also contain every word in
    that phrase, so the phrase's count can never exceed the count of its rarest word.
    Exceeding it is arithmetic proof of dilution, not a judgement call.

    Testing against the rarest constituent word rather than the first word matters: a
    first-word test can never flag "head of people operations", since "head" is common
    enough to mask anything. Rejections are one-directional -- the test can miss mild
    dilution but cannot produce a false positive.
    """
    rejected, kept, notes = {}, {}, []
    for f in FAMILIES:
        clean = []
        for v in f["variants"]:
            n = cached(f"VAR|{v}", titles=[v], ranges=TIER_RANGES["200+"])
            if n is None:
                continue
            words = content_words(v)
            if len(words) < 2:
                clean.append(v)
                kept[v] = n
                continue
            # tightest available bound: the rarest single word in the phrase
            bound, bword = None, None
            for word in words:
                wn = cached(f"VAR|{word}", titles=[word], ranges=TIER_RANGES["200+"])
                if wn is not None and (bound is None or wn < bound):
                    bound, bword = wn, word
            if bound is not None and n > bound:
                rejected[v] = (n, bword, bound)
                notes.append((f["key"], v, n, bword, bound))
            else:
                clean.append(v)
                kept[v] = n
        # never strand a family with no usable variant
        f["clean_variants"] = clean or f["variants"][:1]
    return rejected, kept, notes


# Apollo reports two different caps: a "system limit of 150" terms and a "limit of
# including and excluding 100 job titles". The binding one is 100, exclusive: 99 works,
# 100 is rejected. Measured, not documented.
TITLE_LIMIT = 99


def union_variants(cache):
    """Pick a <=99-term variant set spanning all families, for a deduplicated count.

    Per-family counts cannot be summed: Apollo matches substrings, so "head of customer"
    also counts every "head of customer success", who is a separate family. Only a single
    query dedupes, and a query is capped at 99 title terms against 60 families -- so take
    each family's highest-volume variant first, then spend the remaining budget on the
    biggest families. The result is a deduplicated FLOOR: it uses fewer title strings than
    the full taxonomy, so it under-counts rather than over-counts.
    """
    counts = cache.get("_variant_counts") or {}
    cv = cache.get("_clean_variants") or {}
    ranked = {f["key"]: sorted(cv.get(f["key"], []), key=lambda v: -(counts.get(v) or 0))
              for f in FAMILIES}
    picked = [vs[0] for vs in ranked.values() if vs]
    # remaining budget goes to the next-best variants, biggest first
    extras = sorted(((counts.get(v) or 0, v) for vs in ranked.values() for v in vs[1:]),
                    reverse=True)
    for _, v in extras:
        if len(picked) >= TITLE_LIMIT:
            break
        if v not in picked:
            picked.append(v)
    return picked[:TITLE_LIMIT]


def measure_union(api_key, cache, do_regions):
    """Deduplicated Apollo universe for the whole ICP, via single unioned queries."""
    uv = union_variants(cache)
    cache["_union_variants"] = uv
    jobs = [("_union|GLOBAL|200+", dict(titles=uv, ranges=TIER_RANGES["200+"])),
            ("_union|GLOBAL|200+|verified", dict(titles=uv, ranges=TIER_RANGES["200+"],
                                                verified_only=True))]
    for tier in ("1000+", "5000+"):
        jobs.append((f"_union|GLOBAL|{tier}", dict(titles=uv, ranges=TIER_RANGES[tier])))
    if do_regions:
        for rname, locs in REGION_LOCATIONS.items():
            jobs.append((f"_union|{rname}|200+",
                         dict(titles=uv, ranges=TIER_RANGES["200+"], locations=locs)))
            jobs.append((f"_union|{rname}|200+|verified",
                         dict(titles=uv, ranges=TIER_RANGES["200+"], locations=locs,
                              verified_only=True)))
    print(f"\npass 2: deduplicated union of {len(uv)} title terms across all families")
    fetch_all(api_key, jobs, cache, "union")
    save_cache(cache)


def run(api_key, do_regions, do_verified):
    cache = load_cache()

    def cached(key, **kw):
        """Read-through accessor used by the audit logic after the batch has landed."""
        if key not in cache:
            cache[key] = query(api_key, **kw)
        return cache[key]

    # ---- batch 0: every variant string, plus the leading word of each multi-word
    # variant, so the dilution test has both sides of its comparison.
    jobs = [("_apollo_total_db", dict(titles=[]))]
    seen = set()
    for f in FAMILIES:
        for v in f["variants"]:
            for t in (v, v.split()[0]):
                if t not in seen:
                    seen.add(t)
                    jobs.append((f"VAR|{t}", dict(titles=[t], ranges=TIER_RANGES["200+"])))
    print("pass 0: auditing variant strings for Apollo title dilution")
    fetch_all(api_key, jobs, cache, "variant audit")

    rejected, kept, notes = audit_variants(cached)
    print(f"  {len(kept)} variants kept, {len(rejected)} dropped as diluted")
    for fk, v, n, head, hn in notes:
        print(f"    DROP {fk:<18} {v!r} = {n:,} > {head!r} = {hn:,}")

    # Measurement cells are keyed by family, not by variant list, so a change to a
    # family's clean variants would otherwise leave stale counts cached under a live key.
    # Purge that family's cells whenever its variant list differs from last run.
    prev = cache.get("_clean_variants") or {}
    purged = 0
    for f in FAMILIES:
        if prev.get(f["key"]) != f["clean_variants"]:
            for k in [k for k in cache if k.startswith(f"{f['key']}|")]:
                del cache[k]
                purged += 1
    if purged:
        print(f"  purged {purged} stale cells whose variant list changed")
    cache["_clean_variants"] = {f["key"]: f["clean_variants"] for f in FAMILIES}

    # ---- batch 1: global x 3 size tiers, plus optional verified and regional cuts
    jobs = []
    for f in FAMILIES:
        cv = f["clean_variants"]
        for tier, ranges in TIER_RANGES.items():
            jobs.append((f"{f['key']}|GLOBAL|{tier}", dict(titles=cv, ranges=ranges)))
        if do_verified:
            jobs.append((f"{f['key']}|GLOBAL|200+|verified",
                         dict(titles=cv, ranges=TIER_RANGES["200+"], verified_only=True)))
        if do_regions:
            for rname, locs in REGION_LOCATIONS.items():
                jobs.append((f"{f['key']}|{rname}|200+",
                             dict(titles=cv, ranges=TIER_RANGES["200+"], locations=locs)))
    print(f"\npass 1: measurement cells")
    fetch_all(api_key, jobs, cache, "counts")

    cache["_rejected_variants"] = {k: list(v) for k, v in rejected.items()}
    cache["_variant_counts"] = kept
    save_cache(cache)

    measure_union(api_key, cache, do_regions)

    ok = sum(1 for f in FAMILIES if cache.get(f"{f['key']}|GLOBAL|200+") is not None)
    print(f"\n{len(cache)} cells cached; {ok}/{len(FAMILIES)} families resolved at 200+")
    print("cache: outputs/_apollo_counts_cache.json")
    return cache


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--regions", action="store_true", help="also pull per-region counts")
    ap.add_argument("--verified", action="store_true", help="also pull verified-email counts")
    args = ap.parse_args()

    api_key = os.environ.get("APOLLO_API_KEY")
    if not api_key:
        # Fall back to .env without echoing anything.
        envp = os.path.join(ROOT, ".env")
        if os.path.exists(envp):
            for line in open(envp):
                if line.startswith("APOLLO_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not api_key:
        sys.exit("APOLLO_API_KEY not set. export it or add it to .env")

    run(api_key, args.regions, args.verified)


if __name__ == "__main__":
    main()
