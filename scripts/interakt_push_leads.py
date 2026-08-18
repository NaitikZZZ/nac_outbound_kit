"""Push leads from a CSV into Interakt as tracked WhatsApp users (Track User API).

Defaults to --dry-run: prints what would be sent without calling the API. Pass
--live to actually push. Use --limit to test against a small batch first.

Column names vary across outputs/*.csv, so phone/name/email/company columns are
passed in explicitly rather than guessed.

Usage:
  python scripts/interakt_push_leads.py --csv outputs/austin-summit-campaign-ready.csv \\
      --phone-col phone --first-name-col firstName --last-name-col lastName \\
      --email-col email --company-col company --job-title-col job_title \\
      --tag austin-summit-2026 --limit 5

  # once the dry run looks right:
  python scripts/interakt_push_leads.py --csv outputs/austin-summit-campaign-ready.csv \\
      --phone-col phone --first-name-col firstName --last-name-col lastName \\
      --email-col email --company-col company --job-title-col job_title \\
      --tag austin-summit-2026 --live
"""
import argparse
import csv
import os
import re
import sys
import time

import requests
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, ".env"))

API_KEY = os.getenv("INTERAKT_API_KEY")
TRACK_USER_URL = "https://api.interakt.ai/v1/public/track/users/"

# Growth plan = 300 req/min; stay well under it.
REQUEST_DELAY_SECONDS = 0.25


def digits_only(phone_raw):
    return re.sub(r"\D", "", phone_raw or "")


def build_payload(row, args):
    phone_raw = row.get(args.phone_col, "")
    full_phone = digits_only(phone_raw)
    if not full_phone:
        return None

    traits = {}
    first = row.get(args.first_name_col, "").strip() if args.first_name_col else ""
    last = row.get(args.last_name_col, "").strip() if args.last_name_col else ""
    name = " ".join(p for p in [first, last] if p)
    if name:
        traits["name"] = name
    if args.email_col and row.get(args.email_col, "").strip():
        traits["email"] = row[args.email_col].strip()
    if args.company_col and row.get(args.company_col, "").strip():
        traits["company"] = row[args.company_col].strip()
    if args.job_title_col and row.get(args.job_title_col, "").strip():
        traits["job_title"] = row[args.job_title_col].strip()

    payload = {"fullPhoneNumber": full_phone, "traits": traits}
    if args.tag:
        payload["tags"] = args.tag
    return payload


def push_user(payload):
    resp = requests.post(
        TRACK_USER_URL,
        json=payload,
        headers={
            "Authorization": f"Basic {API_KEY}",
            "Content-Type": "application/json",
        },
        timeout=15,
    )
    return resp.status_code, resp.text


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", required=True, help="Path to the lead CSV")
    parser.add_argument("--phone-col", required=True, help="Column holding the phone number")
    parser.add_argument("--first-name-col", default=None)
    parser.add_argument("--last-name-col", default=None)
    parser.add_argument("--email-col", default=None)
    parser.add_argument("--company-col", default=None)
    parser.add_argument("--job-title-col", default=None)
    parser.add_argument("--tag", action="append", default=None, help="Tag to apply (repeatable)")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N rows with a phone number")
    parser.add_argument("--live", action="store_true", help="Actually call the Interakt API (default is dry-run)")
    args = parser.parse_args()

    if args.live and not API_KEY:
        sys.exit("INTERAKT_API_KEY not set in .env")

    with open(args.csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if args.phone_col not in rows[0]:
        sys.exit(f"Column '{args.phone_col}' not found. Available columns: {list(rows[0].keys())}")

    processed = 0
    skipped_no_phone = 0
    sent_ok = 0
    sent_failed = 0

    for row in rows:
        if args.limit is not None and processed >= args.limit:
            break

        payload = build_payload(row, args)
        if payload is None:
            skipped_no_phone += 1
            continue

        processed += 1

        if not args.live:
            print(f"[DRY RUN] {payload}")
            continue

        status, body = push_user(payload)
        if 200 <= status < 300:
            sent_ok += 1
            print(f"[OK] {payload['fullPhoneNumber']} -> {status}")
        else:
            sent_failed += 1
            print(f"[FAIL] {payload['fullPhoneNumber']} -> {status} {body}")
        time.sleep(REQUEST_DELAY_SECONDS)

    print()
    print(f"Rows with usable phone: {processed}")
    print(f"Rows skipped (no phone): {skipped_no_phone}")
    if args.live:
        print(f"Sent OK: {sent_ok}")
        print(f"Failed: {sent_failed}")
    else:
        print("Dry run only — pass --live to actually push to Interakt.")


if __name__ == "__main__":
    main()
