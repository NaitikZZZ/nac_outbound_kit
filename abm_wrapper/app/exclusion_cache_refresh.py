"""Refreshes the HubSpot exclusion-list cache into Redis, for when this app
is deployed and the local `.claude/skills/hubspot-abm-exclusion/cache/
exclusion_cache.csv` file (gitignored, real client PII, ~221k rows) doesn't
exist in the deployed source at all.

Reuses `.claude/skills/hubspot-abm-exclusion/scripts/refresh_cache.py`'s own
HubSpot-calling logic (`api_request`, `fetch_membership_ids`, `PROPERTIES`,
`LIST_ID`, `PORTAL_ID`) rather than reimplementing it -- only the checkpoint
storage differs: that script checkpoints resumable progress to local files
(meant for a long-lived machine running a daily unattended job); this swaps
those same checkpoints onto Redis keys, since a single Vercel function
invocation has an execution time limit and won't reliably pull ~221k
contacts in one shot. `refresh()` does as much work as fits in a time
budget, saves its checkpoint, and reports whether it's done -- a Vercel Cron
schedule calling the refresh endpoint repeatedly (e.g. every 5-10 minutes)
makes incremental progress until a full pass completes.

While a refresh is in progress, `load_current_cache_rows()` keeps serving
the last fully-completed pass (or None if there's never been one) rather
than a half-written cache -- the "live" keys only get overwritten once a
pass finishes completely.
"""
import importlib.util
import json
import time

from . import kv
from .config import REPO_ROOT

BATCH_TIME_BUDGET_SECONDS = 45  # vercel.json sets maxDuration=60 for this app -- leave buffer
ROWS_PER_CHUNK = 1000


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_refresh_script = _load_module(
    "hubspot_abm_exclusion_refresh_cache",
    REPO_ROOT / ".claude" / "skills" / "hubspot-abm-exclusion" / "scripts" / "refresh_cache.py",
)


def _redis():
    from upstash_redis import Redis
    import os
    url = os.environ.get("UPSTASH_REDIS_REST_URL") or os.environ.get("KV_REST_API_URL", "")
    token = os.environ.get("UPSTASH_REDIS_REST_TOKEN") or os.environ.get("KV_REST_API_TOKEN", "")
    return Redis(url=url, token=token)


def refresh(token):
    """Does as much work as fits in the time budget. Returns a status dict:
    {"complete": bool, "processed": int, "total": int}. Call repeatedly
    (e.g. via Vercel Cron) until "complete" is true."""
    if not kv.available():
        raise RuntimeError("Redis is not configured (UPSTASH_REDIS_REST_URL/TOKEN) -- nothing to refresh into.")

    r = _redis()
    start = time.monotonic()

    membership_raw = r.get("excl:membership_ids")
    if membership_raw:
        ids = json.loads(membership_raw)
    else:
        # Fetched fresh each refresh cycle (not resumed from the original
        # script's own local-file checkpoint) -- see _fetch_all_membership_ids.
        ids = _fetch_all_membership_ids(token)
        r.set("excl:membership_ids", json.dumps(ids))
        r.set("excl:progress", "0")
        r.set("excl:rows_count", "0")

    processed = int(r.get("excl:progress") or "0")
    chunk_count = int(r.get("excl:rows_count") or "0")
    current_chunk_rows = []
    if chunk_count > 0:
        last_chunk_raw = r.get(f"excl:rows:{chunk_count - 1}")
        if last_chunk_raw:
            last_chunk = json.loads(last_chunk_raw)
            if len(last_chunk) < ROWS_PER_CHUNK:
                current_chunk_rows = last_chunk
                chunk_count -= 1

    batch_size = _refresh_script.BATCH_READ_SIZE
    i = processed
    while i < len(ids):
        if time.monotonic() - start > BATCH_TIME_BUDGET_SECONDS:
            break
        chunk_ids = ids[i:i + batch_size]
        body = {
            "properties": _refresh_script.PROPERTIES,
            "inputs": [{"id": str(cid)} for cid in chunk_ids],
        }
        resp = _refresh_script.api_request("POST", "/crm/v3/objects/contacts/batch/read", token, body=body)
        for obj in resp.get("results", []):
            props = obj.get("properties", {}) or {}
            row = {"hs_object_id": obj["id"]}
            row.update({p: props.get(p) or "" for p in _refresh_script.PROPERTIES})
            current_chunk_rows.append(row)
            if len(current_chunk_rows) >= ROWS_PER_CHUNK:
                r.set(f"excl:rows:{chunk_count}", json.dumps(current_chunk_rows))
                chunk_count += 1
                current_chunk_rows = []
        i += batch_size
        r.set("excl:progress", str(min(i, len(ids))))
        r.set("excl:rows_count", str(chunk_count))

    if current_chunk_rows:
        r.set(f"excl:rows:{chunk_count}", json.dumps(current_chunk_rows))
        chunk_count += 1
        r.set("excl:rows_count", str(chunk_count))

    complete = i >= len(ids)
    if complete:
        _finalize(r, chunk_count)
        for j in range(chunk_count):
            r.delete(f"excl:rows:{j}")
        r.delete("excl:membership_ids")
        r.delete("excl:progress")
        r.delete("excl:rows_count")

    return {"complete": complete, "processed": min(i, len(ids)), "total": len(ids)}


def _fetch_all_membership_ids(token):
    """One full (non-chunked) pass over List Memberships -- just IDs, no
    contact properties, so this alone is fast enough to not need its own
    checkpoint even at ~221k members (~885 pages)."""
    ids = []
    after = None
    while True:
        params = {"limit": _refresh_script.MEMBERSHIP_PAGE_SIZE}
        if after:
            params["after"] = after
        resp = _refresh_script.api_request(
            "GET", f"/crm/v3/lists/{_refresh_script.LIST_ID}/memberships", token, params=params
        )
        ids.extend(m["recordId"] for m in resp.get("results", []))
        after = resp.get("paging", {}).get("next", {}).get("after")
        if not after:
            break
    return ids


def _finalize(r, chunk_count):
    """Copies the just-completed pass's chunks into the "live" keys that
    load_current_cache_rows() reads, so an in-progress refresh never
    clobbers the last known-good cache until it's actually done."""
    for j in range(chunk_count):
        raw = r.get(f"excl:rows:{j}")
        r.set(f"excl:live:chunk:{j}", raw)
    r.set("excl:live:chunk_count", str(chunk_count))
    from datetime import datetime, timezone
    r.set("excl:live:meta", json.dumps({
        "list_id": _refresh_script.LIST_ID,
        "portal_id": _refresh_script.PORTAL_ID,
        "refreshed_at": datetime.now(timezone.utc).isoformat(),
    }))


def load_current_cache_rows():
    """Returns (rows, meta) from the last fully-completed refresh, or
    (None, None) if a refresh has never completed. `rows` is a list of dicts
    matching refresh_cache.py's PROPERTIES shape, ready to hand to
    check_exclusions.py's load_cache() (after writing to a temp CSV)."""
    if not kv.available():
        return None, None
    r = _redis()
    chunk_count_raw = r.get("excl:live:chunk_count")
    if not chunk_count_raw:
        return None, None
    chunk_count = int(chunk_count_raw)
    rows = []
    for j in range(chunk_count):
        raw = r.get(f"excl:live:chunk:{j}")
        if raw:
            rows.extend(json.loads(raw))
    meta_raw = r.get("excl:live:meta")
    meta = json.loads(meta_raw) if meta_raw else None
    return rows, meta
