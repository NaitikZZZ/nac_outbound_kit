import os
import csv
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ["SMARTLEAD_API_KEY"]
BASE_URL = "https://server.smartlead.ai/api/v1"

def get(path, params=None):
    params = params or {}
    params["api_key"] = API_KEY
    resp = requests.get(f"{BASE_URL}{path}", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()

def main():
    accounts = get("/email-accounts/")
    if isinstance(accounts, dict):
        accounts = accounts.get("data", accounts.get("email_accounts", []))

    rows = []
    for acc in accounts:
        acc_id = acc.get("id")
        warmup = {}
        try:
            warmup = get(f"/email-accounts/{acc_id}/warmup-stats")
        except requests.HTTPError as e:
            warmup = {"error": str(e)}
        time.sleep(0.3)

        row = {
            "id": acc_id,
            "from_email": acc.get("from_email") or acc.get("email"),
            "from_name": acc.get("from_name"),
            "is_smtp_success": acc.get("is_smtp_success"),
            "is_imap_success": acc.get("is_imap_success"),
            "warmup_enabled": acc.get("warmup_details", {}).get("status") if isinstance(acc.get("warmup_details"), dict) else acc.get("warmup_enabled"),
            "daily_sent_count": acc.get("daily_sent_count"),
            "message_per_day": acc.get("message_per_day"),
            "warmup_raw": json.dumps(warmup),
        }
        rows.append(row)

    os.makedirs("outputs", exist_ok=True)
    out_path = "outputs/smartlead-email-accounts.csv"
    if rows:
        fieldnames = list(rows[0].keys())
        with open(out_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    with open("outputs/_smartlead_accounts_raw.json", "w") as f:
        json.dump(accounts, f, indent=2)

    print(f"Fetched {len(rows)} accounts -> {out_path}")

if __name__ == "__main__":
    main()
