"""
Writes the 6 GTM columns computed by apollo_gtm_columns.py back onto the
matching Apollo ACCOUNT records (not Organizations - custom fields only
exist on your team's saved Accounts, confirmed live 2026-09-15 via
GET /api/v1/typed_custom_fields, modality="account").

Write mechanics confirmed live against a real account (LinkedIn, then
cleared back to blank) before this script was written:
  PUT https://api.apollo.io/api/v1/accounts/{id}
  {"typed_custom_fields": {"<field_id>": "<text>", "<picklist_field_id>": ["<option_id>"]}}
  -> 200, value round-trips on a subsequent GET. See apollo_account_field_ids.py
  for the 6 field IDs (created via Apollo's UI, Add column -> Create field).

Domain -> Apollo Account ID matching uses a per-domain targeted search
(POST /api/v1/accounts/search with q_organization_domains=<domain>, 0
credits - confirmed live 2026-09-15), then verifies every candidate's own
`domain` field is an EXACT match before trusting it. q_organization_domains
alone is NOT trustworthy for exact matching (live testing showed it can
return unrelated companies alongside real hits), but combined with the
client-side exact check it's both fast (~1 call per domain instead of
paginating your whole account base) and accurate (0 false positives across
50 domains tested). If a domain has multiple matching accounts, the first
one found is used.

Usage:
    python3 apollo_write_gtm_fields.py <gtm_columns_csv> [--limit N] [--dry-run]

<gtm_columns_csv> is the output of apollo_gtm_columns.py (needs domain +
the 6 computed columns). --dry-run prints what would be written without
calling PUT. --limit stops after matching N domains, for a quick check
before a full run - ALWAYS run with a small --limit first.
"""
import argparse
import csv
import os
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv()
APOLLO_KEY = os.environ.get('APOLLO_API_KEY')

sys.path.insert(0, os.path.dirname(__file__))
from apollo_gtm_columns import normalize_domain  # noqa: E402
from apollo_account_field_ids import build_typed_custom_fields  # noqa: E402

PER_PAGE = 100
MAX_RETRIES = 5
SECONDS_BETWEEN_CALLS = 3600 / 550  # same throttle as apollo_export_accounts_to_cache.py


def _headers():
    return {'Content-Type': 'application/json', 'x-api-key': APOLLO_KEY}


def _with_retries(fn):
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn()
        except requests.exceptions.RequestException as e:
            last_exc = e
            is_429 = getattr(e, 'response', None) is not None and e.response.status_code == 429
            wait = (30 if is_429 else 5) * attempt
            print(f"  (retry {attempt}/{MAX_RETRIES} after {type(e).__name__}: {e} - waiting {wait}s)", flush=True)
            time.sleep(wait)
    raise last_exc


def search_accounts_by_domain(domain):
    def _call():
        r = requests.post('https://api.apollo.io/api/v1/accounts/search', headers=_headers(),
                           json={'q_organization_domains': domain, 'page': 1, 'per_page': PER_PAGE},
                           timeout=(5, 20))
        r.raise_for_status()
        return r.json().get('accounts', [])
    return _with_retries(_call)


def find_account_ids_by_domain(target_domains, progress=None):
    """target_domains: set of normalized domains to look for. One targeted
    search per domain (0 credits), with candidates filtered client-side to an
    EXACT domain match - q_organization_domains alone isn't reliable for
    exact matching (see module docstring). Returns {domain: account_id}."""
    found = {}
    domains = sorted(target_domains)
    for i, domain in enumerate(domains):
        candidates = search_accounts_by_domain(domain)
        exact = [a for a in candidates if normalize_domain(a.get('domain') or '') == domain]
        if exact:
            found[domain] = exact[0]['id']
        if progress:
            progress(i + 1, len(found), len(domains) - (i + 1))
        time.sleep(SECONDS_BETWEEN_CALLS)
    return found


def write_account_fields(account_id, row):
    payload = {'typed_custom_fields': build_typed_custom_fields(row)}

    def _call():
        r = requests.put(f'https://api.apollo.io/api/v1/accounts/{account_id}',
                          headers=_headers(), json=payload, timeout=(5, 20))
        r.raise_for_status()
        return r.json()
    return _with_retries(_call)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('gtm_columns_csv')
    ap.add_argument('--domain-col', default='organization_website_url')
    ap.add_argument('--limit', type=int, default=None,
                     help='Only process the first N rows - use this for a test run before going wide.')
    ap.add_argument('--dry-run', action='store_true', help="Match domains but don't actually PUT anything.")
    args = ap.parse_args()

    with open(args.gtm_columns_csv, encoding='utf-8', errors='replace') as f:
        rows = list(csv.DictReader(f))
    if args.limit:
        rows = rows[:args.limit]

    by_domain = {}
    for row in rows:
        d = normalize_domain(row.get(args.domain_col, ''))
        if d:
            by_domain[d] = row

    print(f"Looking up Apollo Account IDs for {len(by_domain)} domains "
          f"(0 Apollo credits, one targeted search per domain)...")

    def _progress(checked, matched, remaining):
        print(f"  checked {checked}/{len(by_domain)} domains - matched {matched}, {remaining} left to check",
              flush=True)

    account_ids = find_account_ids_by_domain(set(by_domain.keys()), progress=_progress)

    print(f"\nMatched {len(account_ids)}/{len(by_domain)} domains to an existing Apollo Account.")
    unmatched = set(by_domain.keys()) - set(account_ids.keys())
    if unmatched:
        print(f"Not found as Apollo Accounts (add them to Apollo first if you want fields written): "
              f"{sorted(unmatched)[:10]}{' ...' if len(unmatched) > 10 else ''}")

    written = 0
    for domain, account_id in account_ids.items():
        row = by_domain[domain]
        if args.dry_run:
            print(f"  [dry-run] would write {domain} -> account {account_id}: "
                  f"competitor_match={row.get('competitor_match')}, dream_account={row.get('dream_account')}, "
                  f"partner_tech_match={row.get('partner_tech_match')!r}")
            continue
        write_account_fields(account_id, row)
        written += 1
        print(f"  wrote {domain} -> account {account_id}")
        time.sleep(SECONDS_BETWEEN_CALLS)

    if not args.dry_run:
        print(f"\nWrote GTM fields to {written} Apollo accounts.")


if __name__ == '__main__':
    main()
