"""
Create a HeyReach list and upload leads in batches via the HeyReach API.

NOTE: HeyReach CAMPAIGN creation (with cadence steps) is done in the UI because
step configuration needs fine-tuning. This script handles list creation and
lead upload only. Link the list to a campaign manually in HeyReach UI.

Usage:
  python 07_heyreach_create_list.py \\
    --name "P1_EVENTS_PREEVENT_US_LI_naitik_16APR26" \\
    --leads leads.csv

Required env:
  HEYREACH_API_KEY - your HeyReach API key (from HeyReach Settings)

The leads CSV must have at minimum a 'linkedin_url' column. Optional columns:
  first_name, last_name, email, company, title
"""
import argparse, json, os, sys, time, pandas as pd, requests

BASE = "https://api.heyreach.io/api/public"


def create_list(api_key, name):
    resp = requests.post(
        f"{BASE}/list/CreateEmptyList",
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        json={"name": name, "listType": "USER_LIST"},
        timeout=30
    )
    resp.raise_for_status()
    data = resp.json()
    lid = data.get("id")
    print(f"List created: {name} (ID: {lid})")
    return lid


def add_leads(api_key, list_id, leads_csv):
    df = pd.read_csv(leads_csv)
    df = df[df["linkedin_url"].notna() & (df["linkedin_url"].astype(str).str.startswith("http"))]
    print(f"Loaded {len(df)} leads with valid LinkedIn URLs")

    total_added = 0
    total_failed = 0

    for i in range(0, len(df), 100):
        batch = df.iloc[i:i+100]
        leads = []
        for _, row in batch.iterrows():
            lead = {
                "profileUrl": str(row["linkedin_url"]).strip(),
                "firstName": str(row.get("first_name", "")).strip() if pd.notna(row.get("first_name")) else "",
                "lastName": str(row.get("last_name", "")).strip() if pd.notna(row.get("last_name")) else "",
            }
            # Optional email, company, position
            for src, dst in [("email", "emailAddress"), ("send_to_email", "emailAddress"),
                             ("company", "companyName"), ("title", "position"), ("job_title", "position")]:
                if src in row and pd.notna(row[src]):
                    val = str(row[src]).strip()
                    if val and val not in ("nan", "None") and dst not in lead:
                        lead[dst] = val
            leads.append(lead)

        resp = requests.post(
            f"{BASE}/list/AddLeadsToListV2",
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            json={"listId": list_id, "leads": leads},
            timeout=60
        )
        if resp.status_code == 200:
            data = resp.json()
            added = data.get("addedLeadsCount", 0)
            failed = data.get("failedLeadsCount", 0)
            total_added += added
            total_failed += failed
            print(f"  Batch {i//100+1}: {added} added, {failed} failed")
        else:
            print(f"  Batch {i//100+1} FAILED: {resp.status_code} - {resp.text[:100]}")
            total_failed += len(leads)
        time.sleep(1)

    return total_added, total_failed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True, help="List name (use naming convention)")
    parser.add_argument("--leads", required=True, help="CSV with linkedin_url column")
    args = parser.parse_args()

    api_key = os.environ.get("HEYREACH_API_KEY")
    if not api_key:
        sys.exit("Set HEYREACH_API_KEY env var")

    lid = create_list(api_key, args.name)
    added, failed = add_leads(api_key, lid, args.leads)

    print()
    print(f"=== DONE ===")
    print(f"List ID: {lid}")
    print(f"Name: {args.name}")
    print(f"Leads added: {added}")
    print(f"Leads failed: {failed}")
    print()
    print(f"Next step: In HeyReach UI, create a new campaign, attach this list (ID {lid}),")
    print(f"configure the 5-step cadence (Visit/Like/Connect/DM/Follow-up DM), assign sender.")
