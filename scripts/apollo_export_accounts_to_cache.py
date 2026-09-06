"""
One-time (resumable) export of your team's saved Apollo Accounts into the
shared domain cache, so resolve_company_domains.py never spends a paid
Apollo org-search credit re-discovering a company you already have saved.

Confirmed directly against Apollo's own API docs (docs.apollo.io/reference/
search-for-accounts, fetched 2026-09-01) before writing this:
  - POST /api/v1/accounts/search searches ONLY accounts your team has
    already added (never Apollo's global org database) - 0 credits.
  - Rate limit: 600 calls/hour.
  - Display cap: 50,000 records per search (100/page, up to 500 pages) -
    this is why the script segments by account_stage_id: a single query
    can't reach a 467k-account team, but each stage bucket usually will.
  - Response includes `domain` directly - no additional lookup needed.

This is a different endpoint from the one resolve_company_domains.py uses
for paid resolution (v1/mixed_companies/search, 1 credit/page - searches
Apollo's global database, not your saved accounts). Do not swap this
script to that endpoint.

Usage:
    python3 apollo_export_accounts_to_cache.py --test
        Pulls one page (<=100 accounts) from the first stage and prints
        them - no cache writes. Check your Apollo credit balance in the
        dashboard before and after this to confirm 0 credits yourself
        before trusting the full run below.

    python3 apollo_export_accounts_to_cache.py
        Full resumable export across every account stage. Safe to
        interrupt (Ctrl+C) and re-run - progress is tracked per
        (stage_id, page) in apollo_accounts_export_state.json next to this
        script, and the shared cache is flushed after every page, not just
        at the end.

Rate: throttled to ~550 calls/hour (under the documented 600/hour cap) -
for ~467k accounts (~4,670 pages) that's roughly 8 hours. There is no way
to safely go faster; this is Apollo's own limit, not a script choice.
"""
import os
import sys
import json
import time
import argparse

import requests
from dotenv import load_dotenv

load_dotenv()
APOLLO_KEY = os.environ.get('APOLLO_API_KEY')

sys.path.insert(0, os.path.dirname(__file__))
from resolve_company_domains import load_cache, save_cache, norm, CACHE_FIELDS  # noqa: E402

STATE_PATH = os.path.join(os.path.dirname(__file__), 'apollo_accounts_export_state.json')
SECONDS_BETWEEN_CALLS = 3600 / 550  # ~6.5s -> ~550 calls/hour, under the 600/hour documented cap
PER_PAGE = 100
MAX_PAGES_PER_STAGE = 500  # Apollo's own documented ceiling (50,000 records / 100 per page)


def _headers():
    return {'Content-Type': 'application/json', 'Cache-Control': 'no-cache', 'x-api-key': APOLLO_KEY}


MAX_RETRIES = 5


def _with_retries(fn):
    """A ~8-hour unattended run WILL hit transient network blips (a read
    timeout already killed one run - see git history). Retry with backoff
    rather than crashing the whole job over one flaky call; a 429 gets extra
    breathing room since it means we're pushing the documented rate limit."""
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


def list_account_stages(session):
    def _call():
        r = session.get('https://api.apollo.io/api/v1/account_stages', headers=_headers(), timeout=(5, 15))
        r.raise_for_status()
        return r.json().get('account_stages', [])
    return _with_retries(_call)


def search_accounts_page(session, stage_id, page):
    def _call():
        r = session.post(
            'https://api.apollo.io/api/v1/accounts/search',
            headers=_headers(),
            json={'account_stage_ids': [stage_id], 'page': page, 'per_page': PER_PAGE},
            timeout=(5, 20),
        )
        r.raise_for_status()
        return r.json().get('accounts', [])
    return _with_retries(_call)


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f)
    return {'done_pages': {}, 'stage_exhausted': {}}  # done_pages: {"<stage_id>": last_completed_page}


def save_state(state):
    with open(STATE_PATH, 'w') as f:
        json.dump(state, f, indent=2)


def run_test(session):
    stages = list_account_stages(session)
    if not stages:
        print('No account stages returned - nothing to test against.')
        return
    stage = stages[0]
    print(f"Testing against stage '{stage['display_name']}' (id={stage['id']}), page 1, {PER_PAGE} accounts.")
    print('Check your Apollo credit balance NOW (before), then again after this call.')
    accounts = search_accounts_page(session, stage['id'], 1)
    print(f"Got {len(accounts)} accounts. Sample:")
    for a in accounts[:5]:
        print(f"  {a.get('name')!r} -> domain={a.get('domain')!r}")
    print('\nNo cache writes were made (--test mode). Re-check your credit balance now - it should be unchanged.')


def run_full(session, limit=None):
    stages = list_account_stages(session)
    if not stages:
        print('No account stages returned - nothing to export.')
        return
    print(f"{len(stages)} account stage(s) to walk: {[s['display_name'] for s in stages]}")
    if limit:
        print(f"Stopping after ~{limit} accounts this run (--limit) - re-run without --limit, or with a "
              f"higher one, to continue from where this leaves off (resume state is preserved either way).")

    state = load_state()
    cache = load_cache()
    total_new = 0
    total_seen = 0
    last_flush = time.time()

    for stage in stages:
        if limit and total_seen >= limit:
            break
        sid, sname = stage['id'], stage['display_name']
        if state['stage_exhausted'].get(sid):
            print(f"Stage '{sname}' already fully exported - skipping.")
            continue
        start_page = state['done_pages'].get(sid, 0) + 1
        if start_page > 1:
            print(f"Resuming stage '{sname}' at page {start_page}.")

        for page in range(start_page, MAX_PAGES_PER_STAGE + 1):
            accounts = search_accounts_page(session, sid, page)
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
                    'source': 'Apollo-account-export', 'notes': f"stage={sname}",
                }

            state['done_pages'][sid] = page
            if time.time() - last_flush > 30:
                save_cache(cache)
                save_state(state)
                last_flush = time.time()

            print(f"[{sname}] page {page}: {len(accounts)} accounts "
                  f"(seen {total_seen}, new-to-cache {total_new})", flush=True)

            if len(accounts) < PER_PAGE:
                state['stage_exhausted'][sid] = True
                break
            if limit and total_seen >= limit:
                print(f"\nHit --limit {limit} - stopping mid-stage ('{sname}', through page {page}). "
                      f"Progress is saved; re-run to resume from here.")
                break
            if page == MAX_PAGES_PER_STAGE:
                print(f"WARNING: stage '{sname}' still had a full page at Apollo's own "
                      f"{MAX_PAGES_PER_STAGE}-page cap - this stage likely has more accounts "
                      f"than the 50,000-record display limit allows in one query. Not fully "
                      f"covered; consider splitting it further by account_label_ids.")
            time.sleep(SECONDS_BETWEEN_CALLS)

        save_cache(cache)
        save_state(state)

    save_cache(cache)
    save_state(state)
    print(f"\nDone. {total_seen} accounts seen, {total_new} new cache entries "
          f"(entries with a blank domain were skipped). Cache now has {len(cache)} companies total.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='Pull one page only, print it, write nothing.')
    parser.add_argument('--limit', type=int, default=None,
                         help='Stop after roughly this many accounts (rounds up to the page in progress). '
                              'Re-run (with or without --limit) to resume - progress is saved.')
    args = parser.parse_args()

    if not APOLLO_KEY:
        print('APOLLO_API_KEY not set.')
        sys.exit(1)

    session = requests.Session()
    session.mount('https://', requests.adapters.HTTPAdapter(max_retries=0))

    if args.test:
        run_test(session)
    else:
        run_full(session, limit=args.limit)


if __name__ == '__main__':
    main()
