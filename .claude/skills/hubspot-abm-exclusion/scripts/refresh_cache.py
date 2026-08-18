#!/usr/bin/env python3
"""Pull a HubSpot list's full contact membership into a local cache CSV.

Two-stage pull against HubSpot's public REST API (not the MCP connector,
since the list this targets is 200k+ contacts -- too large to page through
one MCP tool call at a time on a daily unattended schedule):

  1. GET /crm/v3/lists/{listId}/memberships  -> record IDs (paginated)
  2. POST /crm/v3/objects/contacts/batch/read -> properties for those IDs

Requires HUBSPOT_API_KEY (a HubSpot Private App access token with the
crm.objects.contacts.read and crm.lists.read scopes) in .env.

Resumable: a pull over 221k+ contacts on a flaky connection will likely get
interrupted partway through. Progress is checkpointed to cache/_membership_ids.json
(the ID list) and cache/_partial_cache.csv (contact rows fetched so far) so a
re-run picks up where it left off instead of starting over.
"""
import csv
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

API_BASE = "https://api.hubapi.com"
LIST_ID = os.environ.get("HUBSPOT_EXCLUSION_LIST_ID", "28280")
PORTAL_ID = os.environ.get("HUBSPOT_PORTAL_ID", "6512810")

PROPERTIES = [
    "email",
    "firstname",
    "lastname",
    "company",
    "company_domain",
    "hs_linkedin_url",
    "linkedin_url",
    "pb_linkedin_profile_url",
    "linkedin_personal_url",
]

MEMBERSHIP_PAGE_SIZE = 250
BATCH_READ_SIZE = 100
MAX_RETRIES = 8
MAX_BACKOFF_SECONDS = 60

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "cache")
CACHE_CSV = os.path.join(CACHE_DIR, "exclusion_cache.csv")
CACHE_META = os.path.join(CACHE_DIR, "meta.json")
MEMBERSHIP_CHECKPOINT = os.path.join(CACHE_DIR, "_membership_ids.json")
PARTIAL_CSV = os.path.join(CACHE_DIR, "_partial_cache.csv")
PROGRESS_CHECKPOINT = os.path.join(CACHE_DIR, "_progress.json")


def api_request(method, path, token, body=None, params=None):
    url = f"{API_BASE}{path}"
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{query}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")

    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < MAX_RETRIES - 1:
                time.sleep(min(2 ** attempt, MAX_BACKOFF_SECONDS))
                continue
            detail = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HubSpot API error {e.code} on {path}: {detail}") from e
        except (urllib.error.URLError, socket.timeout, OSError) as e:
            if attempt < MAX_RETRIES - 1:
                wait = min(2 ** attempt, MAX_BACKOFF_SECONDS)
                print(f"  network error ({e}), retrying in {wait}s (attempt {attempt + 1}/{MAX_RETRIES})...", file=sys.stderr)
                time.sleep(wait)
                continue
            raise RuntimeError(f"Network error calling {path}: {e}") from e


def load_membership_checkpoint(list_id):
    if not os.path.exists(MEMBERSHIP_CHECKPOINT):
        return None
    with open(MEMBERSHIP_CHECKPOINT, encoding="utf-8") as f:
        data = json.load(f)
    if data.get("list_id") != list_id:
        return None
    return data


def save_membership_checkpoint(list_id, ids, after, complete):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(MEMBERSHIP_CHECKPOINT, "w", encoding="utf-8") as f:
        json.dump({"list_id": list_id, "ids": ids, "after": after, "complete": complete}, f)


def fetch_membership_ids(list_id, token):
    checkpoint = load_membership_checkpoint(list_id)
    if checkpoint and checkpoint.get("complete"):
        print(f"Resuming from checkpoint: {len(checkpoint['ids'])} membership IDs already fetched.", file=sys.stderr)
        return checkpoint["ids"]

    ids = checkpoint["ids"] if checkpoint else []
    after = checkpoint["after"] if checkpoint else None
    if checkpoint:
        print(f"Resuming membership fetch from checkpoint ({len(ids)} IDs so far)...", file=sys.stderr)

    while True:
        params = {"limit": MEMBERSHIP_PAGE_SIZE}
        if after:
            params["after"] = after
        resp = api_request("GET", f"/crm/v3/lists/{list_id}/memberships", token, params=params)
        ids.extend(r["recordId"] for r in resp.get("results", []))
        after = resp.get("paging", {}).get("next", {}).get("after")
        save_membership_checkpoint(list_id, ids, after, complete=not after)
        print(f"  fetched {len(ids)} membership IDs so far...", file=sys.stderr)
        if not after:
            break
    return ids


def load_progress():
    if not os.path.exists(PROGRESS_CHECKPOINT):
        return 0
    with open(PROGRESS_CHECKPOINT, encoding="utf-8") as f:
        return json.load(f).get("processed_count", 0)


def save_progress(processed_count):
    with open(PROGRESS_CHECKPOINT, "w", encoding="utf-8") as f:
        json.dump({"processed_count": processed_count}, f)


def batch_read_contacts(ids, token):
    processed_count = load_progress()
    if processed_count > len(ids):
        processed_count = 0  # stale checkpoint from a different/smaller ID set

    fieldnames = ["hs_object_id"] + PROPERTIES
    mode = "a" if processed_count > 0 and os.path.exists(PARTIAL_CSV) else "w"
    if processed_count > 0:
        print(f"Resuming contact read from {processed_count}/{len(ids)}...", file=sys.stderr)

    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(PARTIAL_CSV, mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if mode == "w":
            writer.writeheader()

        for i in range(processed_count, len(ids), BATCH_READ_SIZE):
            chunk = ids[i:i + BATCH_READ_SIZE]
            body = {
                "properties": PROPERTIES,
                "inputs": [{"id": str(cid)} for cid in chunk],
            }
            resp = api_request("POST", "/crm/v3/objects/contacts/batch/read", token, body=body)
            for obj in resp.get("results", []):
                props = obj.get("properties", {}) or {}
                row = {"hs_object_id": obj["id"]}
                row.update({p: props.get(p) or "" for p in PROPERTIES})
                writer.writerow(row)
            f.flush()
            processed_count = min(i + BATCH_READ_SIZE, len(ids))
            save_progress(processed_count)
            if (i // BATCH_READ_SIZE) % 10 == 0:
                print(f"  read {processed_count}/{len(ids)} contacts...", file=sys.stderr)

    return processed_count


def cleanup_checkpoints():
    for path in (MEMBERSHIP_CHECKPOINT, PROGRESS_CHECKPOINT):
        if os.path.exists(path):
            os.remove(path)


def main():
    token = os.environ.get("HUBSPOT_API_KEY")
    if not token:
        print(
            "ERROR: HUBSPOT_API_KEY not set. Add a HubSpot Private App access token "
            "(scopes: crm.objects.contacts.read, crm.lists.read) to .env as "
            "HUBSPOT_API_KEY=...",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Fetching membership of list {LIST_ID} (portal {PORTAL_ID})...", file=sys.stderr)
    ids = fetch_membership_ids(LIST_ID, token)
    print(f"List has {len(ids)} members. Fetching contact properties...", file=sys.stderr)
    row_count = batch_read_contacts(ids, token)

    os.replace(PARTIAL_CSV, CACHE_CSV)
    cleanup_checkpoints()

    meta = {
        "list_id": LIST_ID,
        "portal_id": PORTAL_ID,
        "refreshed_at": datetime.now(timezone.utc).isoformat(),
        "row_count": row_count,
    }
    with open(CACHE_META, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"Cache refreshed: {row_count} rows written to {CACHE_CSV}", file=sys.stderr)


if __name__ == "__main__":
    main()
