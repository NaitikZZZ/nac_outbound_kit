"""
Bulk-seed the shared domain cache from every HubSpot Company record with a
domain already filled in - the same idea as apollo_export_accounts_to_cache.py
for Apollo Accounts, but for HubSpot's ~212k Company records instead.

Uses the plain List endpoint (GET /crm/v3/objects/companies, cursor-paginated
via paging.next.after), NOT the Search endpoint - HubSpot's Search API hard-
caps at 10,000 total results per query (confirmed via their docs), which
would leave the other ~200k companies unreachable. The List endpoint has no
such cap.

Read-only (list/read only, never writes/updates HubSpot - per this kit's
HubSpot rule). Resumable via a cursor saved to
hubspot_companies_export_state.json; safe to re-run/interrupt at any time.

Usage: python3 hubspot_export_companies_to_cache.py [--limit N]
"""
import os
import sys
import json
import time
import argparse

import requests
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))
from resolve_company_domains import load_cache, save_cache, norm, HUBSPOT_TOKEN  # noqa: E402

PER_PAGE = 100
SECONDS_BETWEEN_CALLS = 0.15  # conservative default; back off harder on 429
MAX_RETRIES = 5
STATE_PATH = os.path.join(os.path.dirname(__file__), 'hubspot_companies_export_state.json')


def _headers():
    return {'Authorization': f'Bearer {HUBSPOT_TOKEN}'}


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


def fetch_page(session, after):
    def _call():
        params = {'properties': 'name,domain', 'limit': PER_PAGE}
        if after:
            params['after'] = after
        r = session.get('https://api.hubapi.com/crm/v3/objects/companies',
                         headers=_headers(), params=params, timeout=(5, 20))
        r.raise_for_status()
        return r.json()
    return _with_retries(_call)


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f)
    return {'after': None, 'done': False}


def save_state(state):
    with open(STATE_PATH, 'w') as f:
        json.dump(state, f, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=None, help='Stop after ~N companies seen this run (for a test slice)')
    args = parser.parse_args()

    if not HUBSPOT_TOKEN:
        print("HUBSPOT_PRIVATE_APP_TOKEN / HUBSPOT_API_KEY not configured - nothing to do.")
        return

    session = requests.Session()
    session.mount('https://', requests.adapters.HTTPAdapter(max_retries=0))

    state = load_state()
    if state.get('done'):
        print("Already fully exported in a prior run. Delete hubspot_companies_export_state.json to redo.")
        return

    cache = load_cache()
    total_seen = 0
    total_new = 0
    last_flush = time.time()

    after = state.get('after')
    while True:
        data = fetch_page(session, after)
        results = data.get('results', [])
        for c in results:
            props = c.get('properties', {}) or {}
            name, domain = props.get('name'), props.get('domain')
            if not name or not domain:
                continue
            key = norm(str(name).strip())
            if key not in cache:
                total_new += 1
            cache[key] = {
                'company_key': key, 'company_name': name, 'domain': domain,
                'linkedin': '', 'country': '', 'city': '',
                'source': 'HubSpot-company-export', 'notes': '',
            }
        total_seen += len(results)

        after = (data.get('paging') or {}).get('next', {}).get('after')
        state['after'] = after
        if time.time() - last_flush > 30:
            save_cache(cache)
            save_state(state)
            last_flush = time.time()

        print(f"page done: {len(results)} companies (seen {total_seen}, new-to-cache {total_new})", flush=True)

        if not after:
            state['done'] = True
            break
        if args.limit and total_seen >= args.limit:
            print(f"Stopping after ~{args.limit} companies this run (--limit) - re-run without --limit "
                  f"to continue from where this leaves off (resume state is preserved either way).")
            break
        time.sleep(SECONDS_BETWEEN_CALLS)

    save_cache(cache)
    save_state(state)
    print(f"\nDone. {total_seen} companies seen, {total_new} new cache entries "
          f"(entries with no name or no domain were skipped). Cache now has {len(cache)} companies total.")


if __name__ == '__main__':
    main()
