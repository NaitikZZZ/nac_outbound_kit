"""
One-off follow-up to apollo_export_accounts_to_cache.py: the 'Cold' account
stage has 426,570 accounts, but api/v1/accounts/search hard-caps any single
query at 50,000 results (100/page x 500 pages) - confirmed live, and neither
account_label_ids (only 80 account-scoped labels exist, covering a small
fraction of Cold with heavy overlap) nor q_organization_name (confirmed via a
live test to be whole-word/token matching, not prefix/substring - no way to
enumerate every distinct word across 426k names) can partition it cleanly.

This is NOT a complete solution - there is no documented way to fully
enumerate a stage this large through this endpoint. It's an accepted partial
improvement: re-querying the same 'Cold' stage under 6 different sort
orders (3 fields x 2 directions) each surfaces a different 50k-account slice
from the same underlying 426,570, so the union across all 6 passes covers
more than any single pass alone - just not all of it, and there is no way to
know in advance how much overlap there'll be between passes.

Usage: python3 apollo_export_cold_sort_passes.py
Resumable (state at apollo_cold_sort_passes_state.json next to this script,
same shape/logic as the main exporter's resume state) and rate-limited the
same way as apollo_export_accounts_to_cache.py (they must never run at the
same time - both share Apollo's 600 calls/hour budget for this endpoint).
"""
import os
import sys
import json
import time

import requests
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))
from resolve_company_domains import load_cache, save_cache, norm  # noqa: E402
from apollo_export_accounts_to_cache import (  # noqa: E402
    _headers, _with_retries, PER_PAGE, MAX_PAGES_PER_STAGE, SECONDS_BETWEEN_CALLS,
)

COLD_STAGE_ID = '649da03725504200a30bf2bd'
STATE_PATH = os.path.join(os.path.dirname(__file__), 'apollo_cold_sort_passes_state.json')

# 3 documented sort fields x 2 directions = 6 passes, each a different 50k
# slice of the same 426,570 accounts - see module docstring for why this
# can't guarantee full coverage, only add to it.
SORT_PASSES = [
    (field, ascending)
    for field in ('account_created_at', 'account_updated_at', 'account_last_activity_date')
    for ascending in (True, False)
]


def search_page(session, sort_field, sort_ascending, page):
    def _call():
        r = session.post(
            'https://api.apollo.io/api/v1/accounts/search',
            headers=_headers(),
            json={'account_stage_ids': [COLD_STAGE_ID], 'page': page, 'per_page': PER_PAGE,
                  'sort_by_field': sort_field, 'sort_ascending': sort_ascending},
            timeout=(5, 20),
        )
        r.raise_for_status()
        return r.json().get('accounts', [])
    return _with_retries(_call)


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f)
    return {'done_pages': {}, 'pass_exhausted': {}}


def save_state(state):
    with open(STATE_PATH, 'w') as f:
        json.dump(state, f, indent=2)


def main():
    session = requests.Session()
    session.mount('https://', requests.adapters.HTTPAdapter(max_retries=0))

    state = load_state()
    cache = load_cache()
    total_new = 0
    total_seen = 0
    last_flush = time.time()

    for sort_field, sort_ascending in SORT_PASSES:
        pass_key = f"{sort_field}:{sort_ascending}"
        if state['pass_exhausted'].get(pass_key):
            print(f"Pass '{pass_key}' already done - skipping.")
            continue
        start_page = state['done_pages'].get(pass_key, 0) + 1
        if start_page > 1:
            print(f"Resuming pass '{pass_key}' at page {start_page}.")

        for page in range(start_page, MAX_PAGES_PER_STAGE + 1):
            accounts = search_page(session, sort_field, sort_ascending, page)
            total_seen += len(accounts)

            for a in accounts:
                name, domain = a.get('name'), a.get('domain')
                if not name or not domain:
                    continue
                key = norm(str(name).strip())
                if key not in cache:
                    total_new += 1
                cache[key] = {
                    'company_key': key, 'company_name': name, 'domain': domain,
                    'linkedin': '', 'country': '', 'city': '',
                    'source': 'Apollo-account-export', 'notes': f"stage=Cold, sort_pass={pass_key}",
                }

            state['done_pages'][pass_key] = page
            if time.time() - last_flush > 30:
                save_cache(cache)
                save_state(state)
                last_flush = time.time()

            print(f"[{pass_key}] page {page}: {len(accounts)} accounts "
                  f"(seen {total_seen}, new-to-cache {total_new})", flush=True)

            if len(accounts) < PER_PAGE:
                state['pass_exhausted'][pass_key] = True
                break
            if page == MAX_PAGES_PER_STAGE:
                print(f"Pass '{pass_key}' hit the 500-page cap too - as expected, this doesn't "
                      f"reach all 426,570 on its own either.")
            time.sleep(SECONDS_BETWEEN_CALLS)

        save_cache(cache)
        save_state(state)

    save_cache(cache)
    save_state(state)
    print(f"\nDone with all 6 sort passes. {total_seen} account-rows seen (with cross-pass overlap), "
          f"{total_new} net-new cache entries. Cache now has {len(cache)} companies total.")


if __name__ == '__main__':
    main()
