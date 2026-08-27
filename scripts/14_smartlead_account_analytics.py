"""
Aggregate Smartlead email-account-level analytics for a date range.

Smartlead's API has no native per-sender-account rollup, so this pulls
per-campaign statistics (date-scoped, exact) and per-campaign attached
accounts, then splits each campaign's sent/opened/replied/bounced/
unsubscribed/clicked counts evenly across its attached sender accounts.
For single-sender campaigns this is exact; for multi-sender campaigns
it's an even-split estimate (Smartlead round-robins sends across
attached accounts but doesn't expose which account sent which email
without a message-history call per lead).

Usage:
    .venv/bin/python3 scripts/14_smartlead_account_analytics.py --start 2026-02-01 --end 2026-08-24
"""
import argparse
import csv
import json
import os
import sys
import time
from collections import defaultdict
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
            wait = min(2 ** attempt, 30)
            time.sleep(wait)
            continue
        if r.status_code >= 500:
            time.sleep(min(2 ** attempt, 15))
            continue
        raise RuntimeError(f"{r.status_code} {r.text[:300]} for {url} {params}")
    raise RuntimeError(f"gave up after {retries} retries: {url} {params}")


def fetch_all_campaigns(api_key):
    return get(f"{BASE}/campaigns", {"api_key": api_key})


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


def fetch_campaign_statistics(api_key, campaign_id, start, end):
    rows = []
    offset = 0
    while True:
        d = get(
            f"{BASE}/campaigns/{campaign_id}/statistics",
            {
                "api_key": api_key,
                "limit": 1000,
                "offset": offset,
                "sent_time_start_date": start,
                "sent_time_end_date": end,
            },
        )
        page = d.get("data", [])
        rows.extend(page)
        total = int(d.get("total_stats", 0))
        offset += len(page)
        if not page or offset >= total:
            break
        time.sleep(0.15)
    return rows


def fetch_campaign_accounts(api_key, campaign_id):
    return get(f"{BASE}/campaigns/{campaign_id}/email-accounts", {"api_key": api_key})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD")
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()

    api_key = load_api_key()
    out_dir = Path(args.out_dir or f"outputs/smartlead-account-analytics_{args.start}_to_{args.end}")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Fetching campaign list...", flush=True)
    campaigns = fetch_all_campaigns(api_key)
    print(f"  {len(campaigns)} campaigns total", flush=True)

    print("Fetching email account roster...", flush=True)
    accounts_meta_raw = fetch_all_email_accounts(api_key)
    print(f"  {len(accounts_meta_raw)} email accounts total", flush=True)

    accounts_meta = {}
    for a in accounts_meta_raw:
        accounts_meta[a["from_email"]] = {
            "from_name": a.get("from_name"),
            "type": a.get("type"),
            "message_per_day": a.get("message_per_day"),
            "daily_sent_count_today": a.get("daily_sent_count"),
            "is_smtp_success": a.get("is_smtp_success"),
            "is_imap_success": a.get("is_imap_success"),
            "smtp_failure_error": a.get("smtp_failure_error"),
            "imap_failure_error": a.get("imap_failure_error"),
            "campaign_count": a.get("campaign_count"),
            "is_connected_to_campaign": a.get("is_connected_to_campaign"),
            "tags": [t.get("tag_name") for t in (a.get("tags") or [])],
            "created_at": a.get("created_at"),
            "warmup_status": (a.get("warmup_details") or {}).get("status"),
            "warmup_reputation": (a.get("warmup_details") or {}).get("warmup_reputation"),
            "warmup_total_sent": (a.get("warmup_details") or {}).get("total_sent_count"),
            "warmup_total_spam": (a.get("warmup_details") or {}).get("total_spam_count"),
        }

    acc = defaultdict(lambda: {
        "sent": 0.0, "opened": 0.0, "replied": 0.0, "bounced": 0.0,
        "unsubscribed": 0.0, "clicked": 0.0,
        "campaigns": set(), "multi_sender_campaigns": set(),
    })

    checkpoint_path = out_dir / "checkpoint.jsonl"
    campaign_rows_out = []
    done_ids = set()
    if checkpoint_path.exists():
        with open(checkpoint_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                done_ids.add(row["campaign_id"])
                campaign_rows_out.append(row)
                emails = [e for e in row["attached_account_emails"].split("; ") if e]
                k = row["attached_accounts"]
                for email in emails:
                    a = acc[email]
                    a["sent"] += row["sent"] / k
                    a["opened"] += row["opened"] / k
                    a["replied"] += row["replied"] / k
                    a["bounced"] += row["bounced"] / k
                    a["unsubscribed"] += row["unsubscribed"] / k
                    a["clicked"] += row["clicked"] / k
                    a["campaigns"].add(row["campaign_id"])
                    if k > 1:
                        a["multi_sender_campaigns"].add(row["campaign_id"])
        print(f"Resuming: {len(done_ids)} campaigns already processed in checkpoint.", flush=True)

    n = len(campaigns)
    checkpoint_f = open(checkpoint_path, "a")
    for i, camp in enumerate(campaigns):
        cid = camp["id"]
        if cid in done_ids:
            continue
        if (i + 1) % 25 == 0 or i == 0:
            print(f"  [{i+1}/{n}] campaign {cid} ({camp.get('status')})", flush=True)
        try:
            stats = fetch_campaign_statistics(api_key, cid, args.start, args.end)

            sent = len(stats)
            if sent == 0:
                continue

            opened = sum(1 for r in stats if r.get("open_time"))
            replied = sum(1 for r in stats if r.get("reply_time"))
            bounced = sum(1 for r in stats if r.get("is_bounced"))
            unsub = sum(1 for r in stats if r.get("is_unsubscribed"))
            clicked = sum(1 for r in stats if r.get("click_time"))

            camp_accounts = fetch_campaign_accounts(api_key, cid)
            emails = [a["from_email"] for a in camp_accounts] or ["UNKNOWN_UNATTACHED"]
            k = len(emails)

            row = {
                "campaign_id": cid, "campaign_name": camp.get("name"),
                "status": camp.get("status"), "sent": sent, "opened": opened,
                "replied": replied, "bounced": bounced, "unsubscribed": unsub,
                "clicked": clicked, "attached_accounts": k,
                "attached_account_emails": "; ".join(emails),
            }
            campaign_rows_out.append(row)
            checkpoint_f.write(json.dumps(row) + "\n")
            checkpoint_f.flush()

            for email in emails:
                a = acc[email]
                a["sent"] += sent / k
                a["opened"] += opened / k
                a["replied"] += replied / k
                a["bounced"] += bounced / k
                a["unsubscribed"] += unsub / k
                a["clicked"] += clicked / k
                a["campaigns"].add(cid)
                if k > 1:
                    a["multi_sender_campaigns"].add(cid)
        except Exception as e:
            print(f"    ERROR on campaign {cid}: {e}", flush=True)
            continue

        time.sleep(0.15)

    checkpoint_f.close()
    print(f"Done. {len(acc)} accounts had activity in range.", flush=True)

    account_rows = []
    for email, a in acc.items():
        meta = accounts_meta.get(email, {})
        sent = round(a["sent"])
        replied = round(a["replied"])
        bounced = round(a["bounced"])
        opened = round(a["opened"])
        clicked = round(a["clicked"])
        unsub = round(a["unsubscribed"])
        account_rows.append({
            "from_email": email,
            "from_name": meta.get("from_name"),
            "attribution": "estimated" if a["multi_sender_campaigns"] else "exact",
            "sent": sent,
            "opened": opened,
            "replied": replied,
            "bounced": bounced,
            "clicked": clicked,
            "unsubscribed": unsub,
            "reply_rate_pct": round(replied / sent * 100, 2) if sent else 0,
            "bounce_rate_pct": round(bounced / sent * 100, 2) if sent else 0,
            "open_rate_pct": round(opened / sent * 100, 2) if sent else 0,
            "click_rate_pct": round(clicked / sent * 100, 2) if sent else 0,
            "campaigns_used_in": len(a["campaigns"]),
            "multi_sender_campaigns": len(a["multi_sender_campaigns"]),
            "account_type": meta.get("type"),
            "daily_send_limit": meta.get("message_per_day"),
            "smtp_connected": meta.get("is_smtp_success"),
            "imap_connected": meta.get("is_imap_success"),
            "smtp_failure_error": meta.get("smtp_failure_error"),
            "warmup_status": meta.get("warmup_status"),
            "warmup_reputation": meta.get("warmup_reputation"),
            "warmup_total_sent": meta.get("warmup_total_sent"),
            "warmup_total_spam": meta.get("warmup_total_spam"),
            "tags": "; ".join(meta.get("tags") or []),
            "lifetime_campaign_count": meta.get("campaign_count"),
            "account_created_at": meta.get("created_at"),
        })

    # accounts with zero activity in range but that exist in workspace
    active_emails = set(acc.keys())
    for email, meta in accounts_meta.items():
        if email in active_emails:
            continue
        account_rows.append({
            "from_email": email, "from_name": meta.get("from_name"),
            "attribution": "no_activity_in_range",
            "sent": 0, "opened": 0, "replied": 0, "bounced": 0, "clicked": 0,
            "unsubscribed": 0, "reply_rate_pct": 0, "bounce_rate_pct": 0,
            "open_rate_pct": 0, "click_rate_pct": 0, "campaigns_used_in": 0,
            "multi_sender_campaigns": 0, "account_type": meta.get("type"),
            "daily_send_limit": meta.get("message_per_day"),
            "smtp_connected": meta.get("is_smtp_success"),
            "imap_connected": meta.get("is_imap_success"),
            "smtp_failure_error": meta.get("smtp_failure_error"),
            "warmup_status": meta.get("warmup_status"),
            "warmup_reputation": meta.get("warmup_reputation"),
            "warmup_total_sent": meta.get("warmup_total_sent"),
            "warmup_total_spam": meta.get("warmup_total_spam"),
            "tags": "; ".join(meta.get("tags") or []),
            "lifetime_campaign_count": meta.get("campaign_count"),
            "account_created_at": meta.get("created_at"),
        })

    account_rows.sort(key=lambda r: r["sent"], reverse=True)

    with open(out_dir / "account_analytics.json", "w") as f:
        json.dump(account_rows, f, indent=2)

    with open(out_dir / "account_analytics.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(account_rows[0].keys()))
        w.writeheader()
        w.writerows(account_rows)

    with open(out_dir / "campaign_breakdown.csv", "w", newline="") as f:
        if campaign_rows_out:
            w = csv.DictWriter(f, fieldnames=list(campaign_rows_out[0].keys()))
            w.writeheader()
            w.writerows(campaign_rows_out)

    print(f"Wrote {out_dir}/account_analytics.csv ({len(account_rows)} accounts)")
    print(f"Wrote {out_dir}/campaign_breakdown.csv ({len(campaign_rows_out)} campaigns with activity)")


if __name__ == "__main__":
    main()
