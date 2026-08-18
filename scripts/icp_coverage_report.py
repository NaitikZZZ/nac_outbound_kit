"""Build outputs/icp-tam-sam-som-report.md from the model, plus Apollo if measured.

Runs standalone. If outputs/_apollo_counts_cache.json exists (written by
apollo_title_counts.py) the Apollo coverage section is populated with measured counts;
otherwise that section says what is still missing rather than guessing.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tam_sam_som as m  # noqa: E402
from icp_titles import FAMILIES  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "outputs")
CACHE = os.path.join(OUT, "_apollo_counts_cache.json")


def fmt(n):
    return f"{round(n):,}"


def pct(a, b):
    return f"{100.0 * a / b:.1f}%" if b else "n/a"


def main():
    lines = []
    w = lines.append

    tiers = {}
    for tier, bands in m.SIZE_TIERS.items():
        tot, per_region, per_family = m.compute(bands, FAMILIES)
        tiers[tier] = (tot, per_region, per_family)

    _, per_region_200, per_family_200 = tiers["200+"]

    w("# Xoxoday ICP: TAM / SAM / SOM and data availability\n")
    w("Source ICP: `ABM_Campaign_Planner_v2(Planner).csv` (609 planned campaigns, "
      "206 raw persona strings, three products).\n")
    w(f"Raw personas collapse into **{len(FAMILIES)} canonical title families**. Full per-title table "
      "in `icp-title-universe.csv`; per-region in `icp-region-coverage.csv`.\n")

    # ------------------------------------------------------------------ funnel
    w("## 1. The funnel\n")
    w("| Stage | 200+ employees | 1000+ | 5000+ | What it means |")
    w("|---|---:|---:|---:|---|")
    w("| Accounts in scope | " + " | ".join(
        fmt(sum(m.ACCOUNTS_BY_BAND[b] for b in m.SIZE_TIERS[t])) for t in m.SIZE_TIERS)
      + " | Companies worldwide at that headcount |")
    for key, label, note in [
        ("tam", "**TAM** contacts", "Everyone on earth holding an in-ICP title"),
        ("sam_addressable", "**SAM** addressable", "Cold-email addressable: language, GDPR, cloud-tech adoption, Xoxoday GTM presence"),
        ("sam_sourceable", "**SAM** sourceable", "A record with a findable business email exists somewhere"),
        ("sam_verified", "**SAM** verified-email", "That email survives verification and is safe to send"),
    ]:
        w(f"| {label} | " + " | ".join(fmt(tiers[t][0][key]) for t in m.SIZE_TIERS)
          + f" | {note} |")
    w("| Data availability | " + " | ".join(
        pct(tiers[t][0]["sam_verified"], tiers[t][0]["tam"]) for t in m.SIZE_TIERS)
      + " | Verified-email SAM as a share of TAM |")
    w("")
    w(f"Account universe is a Zipf tail (exponent {m.ZIPF}) anchored on Statista's "
      f"~{fmt(m.ANCHOR_N)} companies worldwide at {m.ANCHOR_SIZE}+ employees.\n")

    # ---------------------------------------------------------------- by product
    w("## 2. By product\n")
    w("| Product | Title families | TAM | SAM addressable | SAM verified-email | Availability |")
    w("|---|---:|---:|---:|---:|---:|")
    for prod in m.INDUSTRY_FIT:
        fams = [f for f in FAMILIES if prod in f["products"]]
        tot, _, _ = m.compute(m.SIZE_TIERS["200+"], fams)
        w(f"| {prod} | {len(fams)} | {fmt(tot['tam'])} | {fmt(tot['sam_addressable'])} "
          f"| {fmt(tot['sam_verified'])} | {pct(tot['sam_verified'], tot['tam'])} |")
    w("")
    w("Products overlap on shared titles (a CMO is both a Loyalife and a Plum target), "
      "so these columns sum to more than the deduplicated total in section 1.\n")

    # ----------------------------------------------------------------- by region
    w("## 3. Data availability by region\n")
    _av = [100.0 * v["sam_verified"] / v["tam"] for v in per_region_200.values() if v["tam"]]
    _lo = min(per_region_200.items(), key=lambda x: x[1]["sam_verified"] / x[1]["tam"])
    _hi = max(per_region_200.items(), key=lambda x: x[1]["sam_verified"] / x[1]["tam"])
    w("This is the answer to \"what % of data is available across the globe\": it is not "
      f"one number. It runs from {min(_av):.1f}% ({_lo[0]}) to {max(_av):.1f}% "
      f"({_hi[0]}), a {max(_av)/min(_av):.0f}x spread, against a global blended "
      f"{pct(tiers['200+'][0]['sam_verified'], tiers['200+'][0]['tam'])}.\n")
    w("| Region | Accounts 200+ | TAM contacts | ICP reachable | Verified-email SAM | "
      "Availability | profile | email find | verify |")
    w("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for rname, row in sorted(per_region_200.items(), key=lambda x: -x[1]["sam_verified"]):
        r = m.REGIONS[rname]
        w(f"| {rname} | {fmt(row['accounts'])} | {fmt(row['tam'])} | "
          f"{fmt(row['sam_addressable'])} | {fmt(row['sam_verified'])} | "
          f"**{pct(row['sam_verified'], row['tam'])}** | {int(r['profile']*100)}% | "
          f"{int(r['email']*100)}% | {int(r['verified']*100)}% |")
    w("")

    # ------------------------------------------------------------------- titles
    w("## 4. Core titles by global scale\n")
    w("Top 20 by TAM. `% of accounts` is how many companies have the role at all; "
      "`findability` is how well data vendors index the title string.\n")
    w("| # | Title family | Products | Role | % of accounts | Findability | TAM | "
      "Verified-email SAM | Availability |")
    w("|---:|---|---|---|---:|---:|---:|---:|---:|")
    ranked = sorted(per_family_200.items(), key=lambda x: -x[1]["tam"])
    for i, (k, v) in enumerate(ranked[:20], 1):
        w(f"| {i} | {v['label']} | {v['products']} | {v['role']} | "
          f"{v['breadth']*100:.0f}% | {v['findability']:.2f} | {fmt(v['tam'])} | "
          f"{fmt(v['sam_verified'])} | {pct(v['sam_verified'], v['tam'])} |")
    w("")
    w("Thinnest 8, where the title barely exists as a global population:\n")
    w("| Title family | % of accounts | TAM | Verified-email SAM |")
    w("|---|---:|---:|---:|")
    for k, v in ranked[-8:]:
        w(f"| {v['label']} | {v['breadth']*100:.1f}% | {fmt(v['tam'])} | "
          f"{fmt(v['sam_verified'])} |")
    w("")

    # ---------------------------------------------------------------------- SOM
    w("## 5. SOM: what you can actually work in 12 months\n")
    w(f"Measured from the planner: 475 campaigns carry a sequence length, mean "
      f"**{m.PLANNER_MEAN_STEPS} steps** (357 are single-step one-use-case sends; the P1 "
      f"flagship personas run 9-15). Touches per prospect is what bounds SOM, so it is "
      f"shown as a sensitivity grid at {m.SENDS_PER_MAILBOX_DAY} sends/mailbox/day over "
      f"{m.WORKING_DAYS} working days.\n")
    w("| Sending capacity | " + " | ".join(f"@ {k}" for k in m.TOUCH_SCENARIOS)
      + " | LinkedIn lane |")
    w("|---|" + "---:|" * (len(m.TOUCH_SCENARIOS) + 1))
    for name, n in m.CAPACITY_TIERS.items():
        s = m.som(n)
        w(f"| {name} | " + " | ".join(fmt(s[f"prospects_at_{k}"]) for k in m.TOUCH_SCENARIOS)
          + f" | {fmt(s['li_prospects_yr'])} |")
    w("")
    verified_200 = tiers["200+"][0]["sam_verified"]
    s50 = m.som(50)["prospects_at_consolidated (4)"]
    w(f"At 50 mailboxes and a consolidated 4-step cadence you can touch ~{fmt(s50)} "
      f"unique prospects a year, which is **{pct(s50, verified_200)}** of the "
      f"{fmt(verified_200)} verified-email SAM at 200+. Capacity is not the binding "
      f"constraint on the global ICP; data availability and list quality are.\n")

    # -------------------------------------------------------------------- Apollo
    w("## 6. Apollo coverage (measured)\n")
    if os.path.exists(CACHE):
        from apollo_title_counts import REGION_LOCATIONS
        cache = json.load(open(CACHE))
        db_total = cache.get("_apollo_total_db")
        uni = cache.get("_union_variants") or []
        g200 = cache.get("_union|GLOBAL|200+")
        g200v = cache.get("_union|GLOBAL|200+|verified")

        if db_total:
            w(f"Apollo's whole database returns **{fmt(db_total)}** records unfiltered, "
              f"matching its published ~245M. `total_entries` is not capped, so it is a "
              f"usable population count.\n")

        w("### How these numbers were made honest\n")
        w("Two corrections, both of which changed the answer materially:\n")
        rejected = cache.get("_rejected_variants") or {}
        if rejected:
            w(f"**1. Apollo over-matches title phrases.** {len(rejected)} variant strings "
              f"returned more records than their own rarest word, which is arithmetically "
              f"impossible for a genuine phrase match and proves the phrase was matched "
              f"loosely. They were dropped before counting.\n")
            w("| Dropped variant | Apollo returned | Rarest word | Its count |")
            w("|---|---:|---|---:|")
            for v, (n, head, hn) in sorted(rejected.items(), key=lambda x: -x[1][0])[:6]:
                w(f"| `{v}` | {fmt(n)} | `{head}` | {fmt(hn)} |")
            w("")
        w("**2. Per-family counts cannot be summed.** Apollo matches substrings, so "
          "`head of customer` also counts every *head of customer success*, who belongs "
          "to a different family. Summing the 60 families gives an inflated total. Only a "
          "single query dedupes, and Apollo caps a query at 99 title terms (measured: 99 "
          "works, 100 is rejected), so the headline below unions "
          f"{len(uni)} terms spanning all 60 families.\n")

        if g200:
            w("### The deduplicated answer\n")
            w("| Cut | Apollo records | Verified email | Verified rate |")
            w("|---|---:|---:|---:|")
            for tier in ("200+", "1000+", "5000+"):
                n = cache.get(f"_union|GLOBAL|{tier}")
                nv = cache.get(f"_union|GLOBAL|{tier}|verified")
                if n:
                    w(f"| Global, {tier} employees | {fmt(n)} | "
                      f"{fmt(nv) if nv else '-'} | {pct(nv, n) if nv else '-'} |")
            w("")
            if db_total:
                w(f"- The entire Xoxoday ICP is **{pct(g200, db_total)}** of Apollo's "
                  f"database: {fmt(g200)} of {fmt(db_total)} records.")
            if g200v:
                w(f"- Of those, **{fmt(g200v)}** carry a verified email, "
                  f"**{pct(g200v, g200)}**.")
            mod_tam = tiers["200+"][0]["tam"]
            w(f"- Against the modelled TAM of {fmt(mod_tam)}, Apollo holds "
              f"**{pct(g200, mod_tam)}**. Treat this as indicative only, for the reason "
              f"in the calibration note below.\n")
            w(f"The union saturates: 50 title terms returns 5,546,173 and 99 returns "
              f"{fmt(g200)}, so the last 49 terms add only ~17%. Widening the taxonomy "
              f"further would not move this number much.\n")

        # ---- regional: the measured answer to "% of data available globally"
        reg = []
        for rname in REGION_LOCATIONS:
            n = cache.get(f"_union|{rname}|200+")
            nv = cache.get(f"_union|{rname}|200+|verified")
            if n:
                reg.append((rname, n, nv))
        if reg:
            w("### Apollo data availability by region\n")
            w("This is the measured counterpart to section 3. `Verified rate` is Apollo's "
              "own email-verification pass rate for in-ICP contacts in that region, and it "
              "is the single most decision-relevant number in this report.\n")
            w("| Region | Apollo records | Verified email | Verified rate | "
              "Modelled verify % | Model error |")
            w("|---|---:|---:|---:|---:|---:|")
            for rname, n, nv in sorted(reg, key=lambda x: -(x[2] or 0)):
                mr = m.REGIONS.get(rname)
                mv = f"{int(mr['verified'] * 100)}%" if mr else "-"
                err = "-"
                if mr and nv:
                    err = f"{(nv / n) / mr['verified']:.2f}x"
                w(f"| {rname} | {fmt(n)} | {fmt(nv) if nv else '-'} | "
                  f"**{pct(nv, n) if nv else '-'}** | {mv} | {err} |")
            w("")
            best = max(reg, key=lambda x: (x[2] or 0) / x[1])
            worst = min(reg, key=lambda x: (x[2] or 0) / x[1])
            w(f"Verified-email rate runs from **{pct(best[2], best[1])}** in {best[0]} "
              f"down to **{pct(worst[2], worst[1])}** in {worst[0]}. Volume and quality "
              f"do not move together: check the large-but-unverified regions before "
              f"committing sending capacity to them.\n")

        # ---- per family, absolute only
        rows = []
        for f in FAMILIES:
            ap = cache.get(f"{f['key']}|GLOBAL|200+")
            apv = cache.get(f"{f['key']}|GLOBAL|200+|verified")
            if ap is not None:
                rows.append((f, ap, apv, per_family_200[f["key"]]))
        if rows:
            w("### By title family\n")
            w("Absolute Apollo counts per family at 200+ employees. **These overlap and "
              "must not be added up.** `Ratio` is Apollo/modelled-TAM; a value above 1.0 "
              "means Apollo's title matching is broader than the family definition, not "
              "that Apollo has more people than exist.\n")
            w("| Title family | Apollo records | Verified | Verified rate | Modelled TAM "
              "| Ratio |")
            w("|---|---:|---:|---:|---:|---:|")
            for f, ap, apv, mod in sorted(rows, key=lambda x: -x[1]):
                ratio = ap / mod["tam"] if mod["tam"] else 0
                flag = " ⚠" if ratio > 1.5 else ""
                w(f"| {f['label']} | {fmt(ap)} | {fmt(apv) if apv else '-'} | "
                  f"{pct(apv, ap) if apv else '-'} | {fmt(mod['tam'])} | "
                  f"{ratio:.2f}x{flag} |")
            w("")
            over = [r for r in rows if r[3]["tam"] and r[1] / r[3]["tam"] > 1.5]
            w(f"{len(over)} of {len(rows)} families are flagged ⚠. For those, the variant "
              f"strings are generic prefixes (`head of customer`, `marketing`) that Apollo "
              f"expands well beyond the intended role. Use their absolute counts, not "
              f"their ratios.\n")

            w("### Calibration: where the model was wrong\n")
            w("The modelled availability in section 3 was calibrated to published "
              "third-party benchmarks. Measurement says those benchmarks were "
              "**pessimistic about Apollo's raw coverage and roughly right about "
              "verification**:\n")
            us = next((r for r in reg if r[0] == "United States"), None)
            if us:
                w(f"- Apollo alone holds {fmt(us[1])} in-ICP US records, against a "
                  f"modelled US TAM of {fmt(per_region_200['United States']['tam'])}. "
                  f"The model's US account universe and seats-per-account are too "
                  f"conservative, or Apollo's employee-size firmographics are inflated. "
                  f"Both are likely true.")
            w("- Apollo's measured verified rates cluster near 70% in Anglo markets and "
              "40-46% in India and SEA. The model assumed 85% and 72-75%. The "
              "**direction** was right, the **absolute level** was optimistic, and the "
              "**Anglo-vs-Asia gap is real and larger than modelled**.")
            w("- Net: treat section 3's regional ranking as sound and its absolute "
              "percentages as soft. The Apollo table above supersedes them.\n")
    else:
        w("**Not yet measured.** Run:\n")
        w("```")
        w("python3 scripts/apollo_title_counts.py --regions --verified")
        w("python3 scripts/icp_coverage_report.py")
        w("```\n")

    # ------------------------------------------------------------------ caveats
    w("## 7. What is measured vs modelled\n")
    w("| Input | Status |")
    w("|---|---|")
    w(f"| {len(FAMILIES)}-family title taxonomy | Derived from your planner |")
    w("| Planner mean sequence length (1.87) | Measured from the planner |")
    w("| ~380k companies at 250+ employees | Statista 2023 |")
    w("| Regional split of large companies | Statista (Asia ~225k, N. America ~41k) |")
    w("| Zipf exponent 1.06 for the size tail | Standard fitted value, not re-fit here |")
    w("| Seats per account per title | **Modelled** org-structure estimate |")
    w("| Breadth (% of accounts with the role) | **Modelled** judgement per title |")
    w("| Findability index | **Modelled**, calibrated to Apollo/Surfe benchmarks |")
    w("| Regional profile / email / verify rates | **Modelled** from published benchmarks |")
    w("| ICP reachability per region | **Modelled** GTM judgement |")
    w("| Apollo record counts | "
      + ("Measured live |" if os.path.exists(CACHE) else "**Pending API key** |"))
    w("")
    w("The modelled rows are where to push back. Seats-per-account and breadth drive TAM "
      "almost entirely; if you disagree with a number, change it in `icp_titles.py` and "
      "re-run.\n")

    path = os.path.join(OUT, "icp-tam-sam-som-report.md")
    with open(path, "w") as f:
        f.write("\n".join(lines))
    print(f"wrote {path} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
