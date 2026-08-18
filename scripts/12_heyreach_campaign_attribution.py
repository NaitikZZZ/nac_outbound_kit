"""
Pull per-lead HeyReach campaign outreach status (connection request sent /
message sent) for campaigns run by a set of sender accounts, then cross-
reference against the dream account list.

Uses:
  POST /campaign/GetAll              -- list campaigns, filter by sender
  POST /campaign/GetLeadsFromCampaign -- per-lead status within a campaign
    leadConnectionStatus: None | ConnectionSent | ConnectionAccepted
    leadMessageStatus:    None | MessageSent | MessageReply
  (both endpoints paginate with offset/limit, capped at 100/page -- confirmed
  live; this differs from MyNetwork/GetMyNetworkForSender, which needs
  pageNumber/pageSize instead. Pagination params are NOT consistent across
  HeyReach endpoints.)

"Outreach initiated" = a connection request was sent (ConnectionSent or
ConnectionAccepted) OR a message was sent (MessageSent or MessageReply) --
this is what distinguishes an actual HeyReach-driven touch from someone who
just happened to already be an organic 1st-degree connection.

Usage:
  python 12_heyreach_campaign_attribution.py
"""
import csv
import importlib.util
import os
import re
import time

import requests
from dotenv import load_dotenv

load_dotenv()

BASE = "https://api.heyreach.io/api/public"
PAGE_SIZE = 100
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DREAM_LIST = os.path.join(ROOT, "outputs", "dream-list-summary-with-LI-verified-2026.csv")
OUT_DIR = os.path.join(ROOT, "outputs", "heyreach_connections")
OUT_RAW = os.path.join(OUT_DIR, "campaign_leads_raw.csv")
OUT_DREAM = os.path.join(OUT_DIR, "dream_account_campaign_outreach.csv")
OUT_DREAM_BY_COMPANY = os.path.join(OUT_DIR, "dream_account_campaign_outreach_by_company.csv")

SENDERS = {
    216387: "Sumit Khandelwal",
    168813: "Gaurav Sava",
    189996: "Akshat Vyas",
    190103: "Rakesh Gopal",
    191598: "Manas Bisht",
}

# Reuse the normalization/domain-root matching logic from script 11 so both
# pulls define "dream account match" the same way.
spec = importlib.util.spec_from_file_location("match_mod", os.path.join(ROOT, "scripts", "11_match_connections_to_dream_accounts.py"))
match_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(match_mod)


def _headers(api_key):
    return {"X-API-Key": api_key, "Content-Type": "application/json"}


def get_relevant_campaigns(api_key):
    campaigns = []
    offset = 0
    while True:
        resp = requests.post(
            f"{BASE}/campaign/GetAll",
            headers=_headers(api_key),
            json={"offset": offset, "limit": PAGE_SIZE},
            timeout=30,
        )
        data = resp.json()
        items = data.get("items", [])
        campaigns.extend(items)
        if offset + PAGE_SIZE >= data.get("totalCount", 0):
            break
        offset += PAGE_SIZE
        time.sleep(0.1)

    sender_ids = set(SENDERS.keys())
    return [c for c in campaigns if sender_ids & set(c.get("campaignAccountIds") or [])]


def fetch_campaign_leads(api_key, campaign_id, campaign_name):
    rows = []
    offset = 0
    total = None
    while total is None or offset < total:
        try:
            resp = requests.post(
                f"{BASE}/campaign/GetLeadsFromCampaign",
                headers=_headers(api_key),
                json={"campaignId": campaign_id, "offset": offset, "limit": PAGE_SIZE},
                timeout=30,
            )
        except requests.exceptions.RequestException as e:
            print(f"    offset {offset} network error: {e}, retrying...")
            time.sleep(5)
            continue
        if resp.status_code != 200:
            print(f"    offset {offset} failed: {resp.status_code} {resp.text[:150]}")
            time.sleep(3)
            continue
        data = resp.json()
        total = data.get("totalCount", 0)
        items = data.get("items", [])
        if not items:
            break
        for it in items:
            sender_id = it.get("linkedInSenderId")
            if sender_id not in SENDERS:
                continue
            profile = it.get("linkedInUserProfile") or {}
            conn_status = it.get("leadConnectionStatus")
            msg_status = it.get("leadMessageStatus")
            outreach_initiated = conn_status in ("ConnectionSent", "ConnectionAccepted") or msg_status in ("MessageSent", "MessageReply")
            rows.append({
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "sender": SENDERS[sender_id],
                "leadConnectionStatus": conn_status,
                "leadMessageStatus": msg_status,
                "outreach_initiated": outreach_initiated,
                "firstName": profile.get("firstName"),
                "lastName": profile.get("lastName"),
                "companyName": profile.get("companyName"),
                "position": profile.get("position"),
                "location": profile.get("location"),
                "profileUrl": profile.get("profileUrl"),
            })
        offset += len(items)
        time.sleep(0.1)
    return rows


if __name__ == "__main__":
    api_key = os.environ.get("HEYREACH_API_KEY")
    if not api_key:
        raise SystemExit("Set HEYREACH_API_KEY env var")

    os.makedirs(OUT_DIR, exist_ok=True)

    campaigns = get_relevant_campaigns(api_key)
    print(f"Found {len(campaigns)} campaigns run by the 5 senders")

    all_rows = []
    for c in campaigns:
        print(f"Fetching leads for campaign {c['id']} ({c['name']})...")
        rows = fetch_campaign_leads(api_key, c["id"], c["name"])
        print(f"  -> {len(rows)} leads (from our 5 senders)")
        all_rows.extend(rows)

    fieldnames = [
        "campaign_id", "campaign_name", "sender", "leadConnectionStatus",
        "leadMessageStatus", "outreach_initiated", "firstName", "lastName",
        "companyName", "position", "location", "profileUrl",
    ]
    with open(OUT_RAW, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"\nSaved raw campaign leads: {OUT_RAW} ({len(all_rows)} rows)")

    initiated = [r for r in all_rows if r["outreach_initiated"]]
    print(f"Rows with an actual connection request or message sent: {len(initiated)}")

    dream_rows, by_name, by_domain = match_mod.load_dream_accounts()
    matched = []
    company_hits = {}
    for row in initiated:
        dream_row, match_type = match_mod.match_company(row["companyName"], by_name, by_domain)
        if not dream_row:
            continue
        key = dream_row["Company name"]
        company_hits.setdefault(key, []).append(row)
        matched.append({
            "dream_company": key,
            "domain": dream_row["Company Domain Name"],
            "use_case": dream_row["Use Case"],
            "company_owner": dream_row["Company owner"],
            "match_type": match_type,
            **row,
        })

    print(f"Matched {len(matched)} campaign-touched leads to {len(company_hits)} dream accounts")

    out_fieldnames = ["dream_company", "domain", "use_case", "company_owner", "match_type"] + fieldnames
    with open(OUT_DREAM, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fieldnames)
        writer.writeheader()
        writer.writerows(matched)
    print(f"Saved: {OUT_DREAM}")

    with open(OUT_DREAM_BY_COMPANY, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["dream_company", "domain", "use_case", "company_owner", "outreach_touched_count", "senders"])
        for key, hits in sorted(company_hits.items(), key=lambda kv: -len(kv[1])):
            dream_row = by_name.get(match_mod.normalize_name(key)) or next(r for r in dream_rows if r["Company name"] == key)
            senders = sorted(set(h["sender"] for h in hits))
            writer.writerow([key, dream_row["Company Domain Name"], dream_row["Use Case"], dream_row["Company owner"], len(hits), "; ".join(senders)])
    print(f"Saved: {OUT_DREAM_BY_COMPANY}")
