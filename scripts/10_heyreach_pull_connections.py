"""
Pull all 1st-degree LinkedIn connections for a set of HeyReach sender accounts.

Uses POST /MyNetwork/GetMyNetworkForSender. Confirmed live against the API:
- The page-size param is `pageSize`, NOT `limit` (an earlier version of this
  script used `limit`/`offset`, which the API silently ignores -- it just
  re-returns page 0 every time, so every "page" came back identical and the
  earlier pull was ~99% duplicate rows of the same first 20/100 people).
- `pageSize` is capped at 100 (200+ returns HTTP 400).
- `pageNumber` is 0-indexed; pages don't overlap.

Usage:
  python 10_heyreach_pull_connections.py

Required env:
  HEYREACH_API_KEY - your HeyReach API key
"""
import csv
import os
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv()

BASE = "https://api.heyreach.io/api/public"
PAGE_SIZE = 100
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs", "heyreach_connections")

SENDERS = {
    "Sumit Khandelwal": 216387,
    "Gaurav Sava": 168813,
    "Akshat Vyas": 189996,
    "Rakesh Gopal": 190103,
    "Manas Bisht": 191598,
}

FIELDS = [
    "linkedin_id", "profileUrl", "firstName", "lastName", "headline",
    "location", "companyName", "companyUrl", "position", "about",
    "connections", "followers", "emailAddress", "enrichedEmailAddress",
    "customEmailAddress",
]


def _headers(api_key):
    return {"X-API-Key": api_key, "Content-Type": "application/json"}


def fetch_all_connections(api_key, sender_id, sender_name):
    rows = []
    seen_urls = set()
    page = 0
    total = None
    while total is None or len(rows) < total:
        try:
            resp = requests.post(
                f"{BASE}/MyNetwork/GetMyNetworkForSender",
                headers=_headers(api_key),
                json={"senderId": sender_id, "pageNumber": page, "pageSize": PAGE_SIZE},
                timeout=30,
            )
        except requests.exceptions.RequestException as e:
            print(f"  [{sender_name}] page {page} network error: {e}, retrying...")
            time.sleep(5)
            continue
        if resp.status_code != 200:
            print(f"  [{sender_name}] page {page} failed: {resp.status_code} {resp.text[:150]}")
            time.sleep(3)
            continue
        data = resp.json()
        total = data.get("totalCount", 0)
        items = data.get("items", [])
        if not items:
            break
        new_items = [it for it in items if it["profileUrl"] not in seen_urls]
        if not new_items:
            # a repeated page means we've looped -- stop rather than spin forever
            print(f"  [{sender_name}] page {page} returned no new profiles, stopping")
            break
        for it in new_items:
            seen_urls.add(it["profileUrl"])
        rows.extend(new_items)
        page += 1
        if len(rows) % 1000 < PAGE_SIZE:
            print(f"  [{sender_name}] {len(rows)}/{total}")
        time.sleep(0.15)
    return rows


def write_csv(path, rows, sender_name=None):
    with open(path, "w", newline="") as f:
        fieldnames = FIELDS + (["sender"] if sender_name is None else [])
        writer = csv.DictWriter(f, fieldnames=FIELDS + (["sender"] if sender_name is None else []))
        writer.writeheader()
        for r in rows:
            row = {k: r.get(k) for k in FIELDS}
            if sender_name is None:
                row["sender"] = r.get("_sender")
            writer.writerow(row)


if __name__ == "__main__":
    api_key = os.environ.get("HEYREACH_API_KEY")
    if not api_key:
        sys.exit("Set HEYREACH_API_KEY env var")

    os.makedirs(OUT_DIR, exist_ok=True)

    combined = []
    for name, sid in SENDERS.items():
        print(f"Fetching connections for {name} (sender {sid})...")
        rows = fetch_all_connections(api_key, sid, name)
        print(f"  -> {len(rows)} connections")

        safe_name = name.lower().replace(" ", "_")
        out_path = os.path.join(OUT_DIR, f"{safe_name}.csv")
        write_csv(out_path, rows, sender_name=name)
        print(f"  saved: {out_path}")

        for r in rows:
            r["_sender"] = name
        combined.extend(rows)

    combined_path = os.path.join(OUT_DIR, "all_connections.csv")
    write_csv(combined_path, combined, sender_name=None)

    print()
    print("=== DONE ===")
    print(f"Total connections pulled: {len(combined)}")
    print(f"Combined file: {combined_path}")
