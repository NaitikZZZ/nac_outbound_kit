"""Log events against Interakt users via the Track Events API, to trigger
automated campaigns (e.g. "Replied To Email", "Demo Booked").

Same events logged at different times don't replace each other — they stack
on a timeline — so this is safe to re-run without worrying about clobbering
prior data. Defaults to --dry-run; pass --live to actually push.

Usage:
  python scripts/interakt_track_event.py --csv outputs/austin-summit-campaign-ready.csv \\
      --phone-col phone --event-name "Attended Austin Summit" \\
      --trait company=company --trait job_title=job_title --limit 3

  # once the dry run looks right:
  python scripts/interakt_track_event.py --csv outputs/austin-summit-campaign-ready.csv \\
      --phone-col phone --event-name "Attended Austin Summit" \\
      --trait company=company --trait job_title=job_title --live
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
TRACK_EVENTS_URL = "https://api.interakt.ai/v1/public/track/events/"

REQUEST_DELAY_SECONDS = 0.25


def digits_only(phone_raw):
    return re.sub(r"\D", "", phone_raw or "")


def parse_trait_arg(trait_arg):
    if "=" not in trait_arg:
        sys.exit(f"--trait must be in KEY=COLUMN form, got: {trait_arg}")
    key, col = trait_arg.split("=", 1)
    return key, col


def build_payload(row, args, trait_map):
    phone_raw = row.get(args.phone_col, "")
    full_phone = digits_only(phone_raw)
    if not full_phone:
        return None

    event_name = args.event_name if args.event_name else row.get(args.event_col, "").strip()
    if not event_name:
        return None

    traits = {}
    for key, col in trait_map:
        val = row.get(col, "").strip()
        if val:
            traits[key] = val

    payload = {"fullPhoneNumber": full_phone, "event": event_name}
    if traits:
        payload["traits"] = traits
    if args.user_id_col and row.get(args.user_id_col, "").strip():
        payload["userId"] = row[args.user_id_col].strip()
    return payload


def push_event(payload):
    resp = requests.post(
        TRACK_EVENTS_URL,
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
    parser.add_argument("--phone-col", required=True)
    parser.add_argument("--event-name", default=None, help="Static event name applied to every row")
    parser.add_argument("--event-col", default=None, help="Column holding a per-row event name (use instead of --event-name)")
    parser.add_argument("--trait", action="append", default=None, help="KEY=COLUMN mapping added to the event's traits (repeatable)")
    parser.add_argument("--user-id-col", default=None, help="Column holding an existing Interakt user ID, if known")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--live", action="store_true", help="Actually call the Interakt API (default is dry-run)")
    args = parser.parse_args()

    if not args.event_name and not args.event_col:
        sys.exit("Pass either --event-name (static) or --event-col (per-row)")

    if args.live and not API_KEY:
        sys.exit("INTERAKT_API_KEY not set in .env")

    trait_map = [parse_trait_arg(t) for t in (args.trait or [])]

    with open(args.csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if args.phone_col not in rows[0]:
        sys.exit(f"Column '{args.phone_col}' not found. Available columns: {list(rows[0].keys())}")

    processed = 0
    skipped = 0
    sent_ok = 0
    sent_failed = 0

    for row in rows:
        if args.limit is not None and processed >= args.limit:
            break

        payload = build_payload(row, args, trait_map)
        if payload is None:
            skipped += 1
            continue

        processed += 1

        if not args.live:
            print(f"[DRY RUN] {payload}")
            continue

        status, body = push_event(payload)
        if 200 <= status < 300:
            sent_ok += 1
            print(f"[OK] {payload['fullPhoneNumber']} -> {status}")
        else:
            sent_failed += 1
            print(f"[FAIL] {payload['fullPhoneNumber']} -> {status} {body}")
        time.sleep(REQUEST_DELAY_SECONDS)

    print()
    print(f"Rows with usable phone+event: {processed}")
    print(f"Rows skipped: {skipped}")
    if args.live:
        print(f"Sent OK: {sent_ok}")
        print(f"Failed: {sent_failed}")
    else:
        print("Dry run only — pass --live to actually push to Interakt.")


if __name__ == "__main__":
    main()
