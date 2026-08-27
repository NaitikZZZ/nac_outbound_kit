"""
List Smartlead sender accounts that have no tags assigned.

Usage:
    .venv/bin/python3 scripts/15_smartlead_list_untagged_accounts.py
"""
import csv
import json
import os
import sys
import time
from pathlib import Path

import requests

BASE = "https://server.smartlead.ai/api/v1"


def load_api_key():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("SMARTLEAD_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    key = os.environ.get("SMARTLEAD_API_KEY")
    if not key:
        sys.exit("SMARTLEAD_API_KEY not found in .env or environment")
    return key


def get(url, params, retries=8):
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=30)
        except requests.exceptions.RequestException:
            time.sleep(min(2 ** attempt, 30))
            continue
        if r.status_code == 200:
            return r.json()
        if r.status_code == 429:
            time.sleep(min(2 ** attempt, 30))
            continue
        if r.status_code >= 500:
            time.sleep(min(2 ** attempt, 15))
            continue
        raise RuntimeError(f"{r.status_code} {r.text[:300]} for {url} {params}")
    raise RuntimeError(f"gave up after {retries} retries: {url} {params}")


def fetch_all_email_accounts(api_key):
    accounts = []
    offset = 0
    while True:
        page = get(f"{BASE}/email-accounts/", {"api_key": api_key, "offset": offset, "limit": 100})
        accounts.extend(page)
        if len(page) < 100:
            break
        offset += 100
        time.sleep(0.15)
    return accounts


def main():
    api_key = load_api_key()
    accounts = fetch_all_email_accounts(api_key)
    print(f"Total accounts in workspace: {len(accounts)}", flush=True)

    untagged = [a for a in accounts if not (a.get("tags") or [])]
    print(f"Untagged accounts: {len(untagged)}", flush=True)

    out_dir = Path("outputs/smartlead-untagged-accounts")
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for a in untagged:
        rows.append({
            "id": a.get("id"),
            "from_email": a.get("from_email"),
            "from_name": a.get("from_name"),
            "domain": (a.get("from_email") or "").split("@")[-1],
            "type": a.get("type"),
            "message_per_day": a.get("message_per_day"),
            "is_smtp_success": a.get("is_smtp_success"),
            "campaign_count": a.get("campaign_count"),
            "created_at": a.get("created_at"),
        })
    rows.sort(key=lambda r: (r["domain"], r["from_email"] or ""))

    with open(out_dir / "untagged_accounts.csv", "w", newline="") as f:
        if rows:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    with open(out_dir / "untagged_accounts.json", "w") as f:
        json.dump(rows, f, indent=2)

    print(f"Wrote {out_dir}/untagged_accounts.csv")

    # Also dump existing tag vocabulary in use, for reference
    tag_vocab = set()
    for a in accounts:
        for t in (a.get("tags") or []):
            tag_vocab.add(t.get("tag_name"))
    print("Existing tags in workspace:", sorted(tag_vocab))


if __name__ == "__main__":
    main()
