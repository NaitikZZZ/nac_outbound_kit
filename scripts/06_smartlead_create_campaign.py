"""
Create a full Smartlead campaign end-to-end:
  1. Create campaign
  2. Save email sequence (5-step or 1-step)
  3. Attach sender email accounts (region-matched)
  4. Set schedule (timezone-aware, with hardcoded defaults)
  5. Configure settings (stop on reply, unsubscribe)
  6. Upload leads (batched at 100 per request)
  7. Leave PAUSED for user review

Usage:
  python 06_smartlead_create_campaign.py \\
    --name "P1_EVENTS_PREEVENT_US_EMAIL_naitik_16APR26" \\
    --leads leads.csv \\
    --sequence sequence.json \\
    --accounts 50

  # Override defaults if needed:
  python 06_smartlead_create_campaign.py \\
    --name "..." --leads ... --sequence ... \\
    --timezone America/Los_Angeles --max-daily 100

Defaults applied automatically (from config/smartlead-campaign-defaults.yaml):
  - Timezone: Asia/Calcutta
  - Schedule: 9am-6pm Mon-Fri
  - Interval: 20 minutes
  - Daily limit: 200 leads/day

Required env:
  SMARTLEAD_API_KEY - your Smartlead API key (from Settings > API Keys)

sequence.json format:
{
  "sequences": [
    {
      "seq_number": 1,
      "seq_delay_details": {"delay_in_days": 0},
      "seq_variants": [
        {"subject": "...", "email_body": "<p>...</p>", "variant_label": "A"},
        {"subject": "...", "email_body": "<p>...</p>", "variant_label": "B"}
      ]
    },
    ...
  ]
}
"""
import argparse, json, os, sys, time, yaml, pandas as pd, requests

BASE = "https://server.smartlead.ai/api/v1"


def load_defaults():
    """Load hardcoded campaign defaults from YAML config."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "smartlead-campaign-defaults.yaml")
    if not os.path.exists(config_path):
        return {}
    with open(config_path) as f:
        return yaml.safe_load(f) or {}


def create_campaign(api_key, name):
    resp = requests.post(
        f"{BASE}/campaigns/create?api_key={api_key}",
        json={"name": name, "client_id": None},
        timeout=30
    )
    resp.raise_for_status()
    data = resp.json()
    cid = data.get("id")
    print(f"Campaign created: {name} (ID: {cid})")
    return cid


def save_sequence(api_key, cid, sequence_json_path):
    with open(sequence_json_path) as f:
        sequence = json.load(f)
    resp = requests.post(
        f"{BASE}/campaigns/{cid}/sequences?api_key={api_key}",
        json=sequence,
        timeout=30
    )
    print(f"Sequence: {resp.status_code} - {resp.text[:80]}")
    return resp.status_code == 200


def attach_accounts(api_key, cid, account_ids):
    for i in range(0, len(account_ids), 50):
        batch = account_ids[i:i+50]
        resp = requests.post(
            f"{BASE}/campaigns/{cid}/email-accounts?api_key={api_key}",
            json={"email_account_ids": batch},
            timeout=30
        )
        print(f"  Accounts batch {i//50+1}: {resp.status_code} ({len(batch)} attached)")
        time.sleep(0.5)


def set_schedule(api_key, cid, timezone, start_hour, end_hour, days=None, min_gap=10, max_daily=50):
    if days is None:
        days = [1, 2, 3, 4, 5]
    resp = requests.post(
        f"{BASE}/campaigns/{cid}/schedule?api_key={api_key}",
        json={
            "timezone": timezone,
            "days_of_the_week": days,
            "start_hour": start_hour,
            "end_hour": end_hour,
            "min_time_btw_emails": min_gap,
            "max_new_leads_per_day": max_daily
        },
        timeout=15
    )
    print(f"Schedule: {resp.status_code}")


def configure_settings(api_key, cid):
    resp = requests.post(
        f"{BASE}/campaigns/{cid}/settings?api_key={api_key}",
        json={
            "stop_lead_settings": "REPLY_TO_AN_EMAIL",
            "send_as_plain_text": False,
            "follow_up_percentage": 100,
            "add_unsubscribe_tag": True
        },
        timeout=15
    )
    print(f"Settings: {resp.status_code}")


def upload_leads(api_key, cid, leads_csv, email_col="send_to_email"):
    df = pd.read_csv(leads_csv)
    total_uploaded = 0
    total_failed = 0
    leads = []
    for _, row in df.iterrows():
        email = str(row.get(email_col, row.get("email", ""))).strip()
        if not email or email == "nan":
            continue

        lead = {
            "email": email,
            "first_name": str(row.get("first_name", "")).strip() if pd.notna(row.get("first_name")) else "",
            "last_name": str(row.get("last_name", "")).strip() if pd.notna(row.get("last_name")) else "",
            "company_name": str(row.get("company", row.get("company_name", ""))).strip() if pd.notna(row.get("company", row.get("company_name"))) else "",
            "phone_number": str(row.get("best_phone", "")).strip() if pd.notna(row.get("best_phone")) else "",
            "linkedin_profile": str(row.get("linkedin_url", "")).strip() if pd.notna(row.get("linkedin_url")) else "",
        }
        # Custom fields
        custom = {}
        for col in ["title", "job_title", "deal_name", "segment"]:
            if col in row and pd.notna(row[col]):
                custom[col] = str(row[col]).strip()
        if custom:
            lead["custom_fields"] = custom
        leads.append(lead)

    for i in range(0, len(leads), 100):
        batch = leads[i:i+100]
        resp = requests.post(
            f"{BASE}/campaigns/{cid}/leads?api_key={api_key}",
            json={
                "lead_list": batch,
                "settings": {
                    "ignore_global_block_list": False,
                    "ignore_unsubscribe_list": False,
                    "ignore_community_bounce_list": False,
                    "ignore_duplicate_leads_in_other_campaign": False
                }
            },
            timeout=60
        )
        if resp.status_code == 200:
            data = resp.json()
            uploaded = data.get("upload_count", len(batch))
            blocked = data.get("block_count", 0)
            total_uploaded += uploaded
            total_failed += blocked
            print(f"  Batch {i//100+1}: {uploaded} uploaded, {blocked} blocked")
        else:
            print(f"  Batch {i//100+1} FAILED: {resp.status_code}")
            total_failed += len(batch)
        time.sleep(1)

    return total_uploaded, total_failed


if __name__ == "__main__":
    defaults = load_defaults()
    sched_defaults = defaults.get("scheduling", {})

    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True, help="Campaign name (use naming convention)")
    parser.add_argument("--leads", required=True, help="Path to leads CSV")
    parser.add_argument("--sequence", required=True, help="Path to sequence JSON file")
    parser.add_argument("--accounts-json", help="JSON file with account IDs list (from Smartlead get_all_email_accounts)")
    parser.add_argument("--num-accounts", type=int, default=50, help="Number of accounts to attach (default 50)")
    parser.add_argument("--timezone", default=sched_defaults.get("timezone", "Asia/Calcutta"), help="IANA timezone (hardcoded default: Asia/Calcutta)")
    parser.add_argument("--start-hour", type=int, default=sched_defaults.get("sending_window", {}).get("start_hour", 9), help="Start hour 0-23 (hardcoded default: 9)")
    parser.add_argument("--end-hour", type=int, default=sched_defaults.get("sending_window", {}).get("end_hour", 18), help="End hour 0-23 (hardcoded default: 18)")
    parser.add_argument("--min-gap", type=int, default=sched_defaults.get("sending_interval_minutes", 20), help="Minutes between emails per inbox (hardcoded default: 20)")
    parser.add_argument("--max-daily", type=int, default=sched_defaults.get("daily_lead_limit", 200), help="Max new leads activated per day (hardcoded default: 200)")
    parser.add_argument("--email-col", default="send_to_email", help="Column in leads CSV with sending email")
    args = parser.parse_args()

    api_key = os.environ.get("SMARTLEAD_API_KEY")
    if not api_key:
        sys.exit("Set SMARTLEAD_API_KEY env var")

    cid = create_campaign(api_key, args.name)
    save_sequence(api_key, cid, args.sequence)

    if args.accounts_json:
        with open(args.accounts_json) as f:
            all_accts = json.load(f)
        account_ids = [a["id"] for a in all_accts[:args.num_accounts]]
        attach_accounts(api_key, cid, account_ids)

    set_schedule(api_key, cid, args.timezone, args.start_hour, args.end_hour,
                 min_gap=args.min_gap, max_daily=args.max_daily)
    configure_settings(api_key, cid)

    uploaded, failed = upload_leads(api_key, cid, args.leads, email_col=args.email_col)

    print()
    print(f"=== DONE ===")
    print(f"Campaign ID: {cid}")
    print(f"Name: {args.name}")
    print(f"Leads uploaded: {uploaded}")
    print(f"Leads blocked: {failed}")
    print(f"Timezone: {args.timezone}")
    print(f"Schedule: {args.start_hour}am-{args.end_hour}pm, {args.min_gap}min interval, {args.max_daily} leads/day")
    print(f"Status: PAUSED (review in Smartlead UI, flip to START when ready)")
