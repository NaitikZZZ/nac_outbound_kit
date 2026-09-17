"""Create a new WhatsApp message template in Interakt for Meta approval.

Covers the plain-text "NoHeader Template" shape only (no header, media, or
buttons) - the create-template endpoint also supports TextHeader, MediaHeader,
Call To Action, Quick Replies, and Carousel templates, none of which are
implemented here; add them if a campaign actually needs one.

This creates a real resource in Interakt/Meta (submitted for template review),
so it defaults to --dry-run; --live requires explicit confirmation from the
user before you run it, every time.

Usage:

    python scripts/interakt_create_template.py \\
        --display-name xoxoday_allindia_reconnect_sep26 \\
        --category marketing \\
        --body "Hi {{1}}, I am Naitik from Xoxoday..." \\
        --body-sample "Naitik" \\
        --live
"""
import argparse
import json
import os
import re
import sys

import requests
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, ".env"))

API_KEY = os.getenv("INTERAKT_API_KEY")
CREATE_TEMPLATE_URL = "https://api.interakt.ai/v1/public/track/templates/"


def auth_headers():
    return {"Authorization": f"Basic {API_KEY}", "Content-Type": "application/json"}


def build_payload(args):
    placeholder_count = len(set(re.findall(r"\{\{(\d+)\}\}", args.body)))
    if placeholder_count != len(args.body_sample or []):
        sys.exit(
            f"Body has {placeholder_count} placeholder(s) ({{1}}, {{2}}, ...) "
            f"but got {len(args.body_sample or [])} --body-sample value(s) - counts must match."
        )

    payload = {
        "display_name": args.display_name,
        "language": args.language,
        "category": args.category,
        "header_format": None,
        "body": args.body,
        "body_text": args.body_sample or [],
    }
    if args.footer:
        payload["footer"] = args.footer
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--display-name", required=True, help="Template name (lowercase/numbers/underscores, Meta convention)")
    parser.add_argument("--language", default="English", help="Must match Meta's language list, e.g. English")
    parser.add_argument("--category", default="Marketing", help="Marketing, Utility, or Authentication")
    parser.add_argument("--body", required=True, help="Template body text with {{1}}, {{2}}... placeholders")
    parser.add_argument("--body-sample", action="append", default=None, help="Sample value for each placeholder, in order (repeatable) - required by Meta for review")
    parser.add_argument("--footer", default=None, help="Optional static footer text")
    parser.add_argument("--live", action="store_true", help="Actually submit to Interakt/Meta (default is dry-run)")
    args = parser.parse_args()

    if not API_KEY:
        sys.exit("INTERAKT_API_KEY not set in .env")

    payload = build_payload(args)

    if not args.live:
        print("[DRY RUN] Would POST to", CREATE_TEMPLATE_URL)
        print(json.dumps(payload, indent=2))
        print("\nPass --live to actually submit this template for Meta approval.")
        return

    resp = requests.post(CREATE_TEMPLATE_URL, json=payload, headers=auth_headers(), timeout=15)
    print(f"Status: {resp.status_code}")
    print(resp.text)
    if 200 <= resp.status_code < 300:
        data = resp.json().get("data", {})
        print(f"\nSubmitted. Interakt name: {data.get('name')}  approval_status: {data.get('approval_status')}")
    else:
        sys.exit("Template creation failed - see response above.")


if __name__ == "__main__":
    main()
