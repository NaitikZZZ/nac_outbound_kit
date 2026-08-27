"""Set time_to_wait_in_mins on every Smartlead email account (min gap between sends per inbox)."""
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ["SMARTLEAD_API_KEY"]
BASE = "https://server.smartlead.ai/api/v1"
MIN_GAP_MINUTES = 15


def list_email_accounts():
    accounts = []
    offset = 0
    while True:
        resp = requests.get(
            f"{BASE}/email-accounts/?api_key={API_KEY}&offset={offset}&limit=100",
            timeout=30,
        )
        resp.raise_for_status()
        page = resp.json()
        accounts.extend(page)
        if len(page) < 100:
            break
        offset += 100
    return accounts


def set_time_gap(account_id, minutes):
    resp = requests.post(
        f"{BASE}/email-accounts/{account_id}?api_key={API_KEY}",
        json={"time_to_wait_in_mins": minutes},
        timeout=15,
    )
    return resp.status_code, resp.text


def main():
    accounts = list_email_accounts()
    print(f"Found {len(accounts)} email accounts")
    ok, failed = 0, []
    for acct in accounts:
        acct_id = acct.get("id")
        email = acct.get("from_email", acct_id)
        status, body = set_time_gap(acct_id, MIN_GAP_MINUTES)
        if status == 200:
            ok += 1
            print(f"  [{status}] {email}")
        else:
            failed.append((email, status, body))
            print(f"  [{status}] {email} -> {body[:200]}")
        time.sleep(0.3)

    print(f"\nDone: {ok}/{len(accounts)} updated to {MIN_GAP_MINUTES} min gap")
    if failed:
        print(f"Failed ({len(failed)}):")
        for email, status, body in failed:
            print(f"  {email}: {status} {body[:200]}")


if __name__ == "__main__":
    main()
