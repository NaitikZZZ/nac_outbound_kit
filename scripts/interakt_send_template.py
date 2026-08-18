"""Send an approved WhatsApp template to leads via Interakt's Send Template API.

This actually messages people — unlike the lead-push script, there is no safe
"just creates a data record" version of this. Defaults to --dry-run; --live
requires explicit confirmation from the user before you run it, every time.

Two modes:

1. Inspect a template first (read-only, safe) to see its body text, variable
   count, and category so you map CSV columns to the right placeholders:

     python scripts/interakt_send_template.py --inspect-template redemption

2. Send it to a CSV of leads, mapping columns to {{1}}, {{2}}... in order:

     python scripts/interakt_send_template.py --csv outputs/austin-summit-campaign-ready.csv \\
         --phone-col phone --template-name redemption --template-category marketing \\
         --language-code en --body-col firstName --limit 3

     # once the dry run looks right:
     python scripts/interakt_send_template.py --csv outputs/austin-summit-campaign-ready.csv \\
         --phone-col phone --template-name redemption --template-category marketing \\
         --language-code en --body-col firstName --live --limit 3
"""
import argparse
import csv
import json
import os
import re
import sys
import time

import requests
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, ".env"))

API_KEY = os.getenv("INTERAKT_API_KEY")
MESSAGE_URL = "https://api.interakt.ai/v1/public/message/"
TEMPLATES_URL = "https://api.interakt.ai/v1/public/track/organization/templates"

REQUEST_DELAY_SECONDS = 0.25


def auth_headers():
    return {"Authorization": f"Basic {API_KEY}", "Content-Type": "application/json"}


def digits_only(phone_raw):
    return re.sub(r"\D", "", phone_raw or "")


def inspect_template(name):
    resp = requests.get(
        TEMPLATES_URL,
        params={"offset": 0, "template_name": name},
        headers=auth_headers(),
        timeout=15,
    )
    if resp.status_code != 200:
        sys.exit(f"Failed to fetch template: {resp.status_code} {resp.text}")

    templates = resp.json().get("results", {}).get("templates", [])
    matches = [t for t in templates if t["name"] == name]
    if not matches:
        sys.exit(f"No template named '{name}' found. Fetched {len(templates)} templates total — check spelling.")

    for t in matches:
        print(json.dumps(t, indent=2))
        body_var_count = len(re.findall(r"\{\{\d+\}\}", t.get("body") or ""))
        print(f"\nBody placeholder count: {body_var_count}")
        print(f"Header format: {t.get('header_format')}")
        print(f"Category: {t.get('category')}  Approval: {t.get('approval_status')}")


def build_payload(row, args):
    phone_raw = row.get(args.phone_col, "")
    full_phone = digits_only(phone_raw)
    if not full_phone:
        return None

    body_values = []
    for col in args.body_col or []:
        body_values.append(row.get(col, "").strip())

    template = {
        "name": args.template_name,
        "languageCode": args.language_code,
        "bodyValues": body_values,
    }
    if args.header_col:
        template["headerValues"] = [row.get(args.header_col, "").strip()]

    payload = {
        "fullPhoneNumber": full_phone,
        "template_category": args.template_category,
        "type": "Template",
        "template": template,
    }
    if args.campaign_id:
        payload["campaignId"] = args.campaign_id
    return payload


def send_message(payload):
    resp = requests.post(MESSAGE_URL, json=payload, headers=auth_headers(), timeout=15)
    return resp.status_code, resp.text


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--inspect-template", default=None, help="Fetch and print a template's structure, then exit")
    parser.add_argument("--csv", default=None, help="Path to the lead CSV")
    parser.add_argument("--phone-col", default=None)
    parser.add_argument("--template-name", default=None)
    parser.add_argument("--template-category", default=None, help="e.g. marketing, utility, authentication — must match the template's approved category")
    parser.add_argument("--language-code", default="en")
    parser.add_argument("--header-col", default=None, help="Column to fill the template's header variable, if any")
    parser.add_argument("--body-col", action="append", default=None, help="Column to fill the next {{n}} body variable, in order (repeatable)")
    parser.add_argument("--campaign-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--live", action="store_true", help="Actually send messages (default is dry-run)")
    args = parser.parse_args()

    if not API_KEY:
        sys.exit("INTERAKT_API_KEY not set in .env")

    if args.inspect_template:
        inspect_template(args.inspect_template)
        return

    required = ["csv", "phone_col", "template_name", "template_category"]
    missing = [r for r in required if not getattr(args, r)]
    if missing:
        sys.exit(f"Missing required args for sending: {', '.join('--' + m.replace('_', '-') for m in missing)}")

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

        status, body = send_message(payload)
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
        print("Dry run only — pass --live to actually send via Interakt.")


if __name__ == "__main__":
    main()
