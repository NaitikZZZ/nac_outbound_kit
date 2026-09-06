"""
Second follow-up to apollo_export_accounts_to_cache.py / apollo_export_cold_sort_passes.py.

The 6 date-sort passes already ran and still can't reach all of Cold's
426,570 accounts - every pass pulls from the same universe just reordered,
so accounts that never land in the top-50k of ANY of the 3 date fields (in
either direction) are permanently unreachable that way, no matter how many
more sort combos you try.

account_label_ids is a genuinely different axis - it's not a date ordering,
it's a real attribute a subset of accounts carry (manually-applied labels
like "CAM 2025", "US ABM", etc). Confirmed live: 80 account-scoped labels
exist account-wide, largest is 33,301 - small enough that intersecting with
account_stage_ids=[Cold] should keep every per-label query well under the
50,000-record cap, so unlike the stage-only or sort-only passes, THIS
splitting axis can actually be fully paginated per bucket, not just capped.

Still not a completeness guarantee for all of Cold (most of its 426,570
accounts appear to carry no label at all, per the earlier finding that total
labeled account-slots account-wide is only 170,574 with overlap) - this is
one more incremental pass, not the final answer.
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
STATE_PATH = os.path.join(os.path.dirname(__file__), 'apollo_cold_label_passes_state.json')


def list_account_labels(session):
    def _call():
        r = session.get('https://api.apollo.io/api/v1/labels', headers=_headers(), timeout=(5, 20))
        r.raise_for_status()
        return r.json()
    labels = _with_retries(_call)
    return [l for l in labels if l.get('modality') == 'accounts']


def search_page(session, label_id, page):
    def _call():
        r = session.post(
            'https://api.apollo.io/api/v1/accounts/search',
            headers=_headers(),
            json={'account_stage_ids': [COLD_STAGE_ID], 'account_label_ids': [label_id],
                  'page': page, 'per_page': PER_PAGE},
            timeout=(5, 20),
        )
        r.raise_for_status()
        return r.json().get('accounts', [])
    return _with_retries(_call)


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f)
    return {'done_pages': {}, 'label_exhausted': {}}


def save_state(state):
    with open(STATE_PATH, 'w') as f:
        json.dump(state, f, indent=2)


def main():
    session = requests.Session()
    session.mount('https://', requests.adapters.HTTPAdapter(max_retries=0))

    labels = list_account_labels(session)
    print(f"{len(labels)} account-scoped labels to check against the Cold stage.", flush=True)

    state = load_state()
    cache = load_cache()
    total_new = 0
    total_seen = 0
    last_flush = time.time()

    for label in labels:
        label_id, label_name = label['id'], label.get('name', '')
        if state['label_exhausted'].get(label_id):
            continue
        start_page = state['done_pages'].get(label_id, 0) + 1

        for page in range(start_page, MAX_PAGES_PER_STAGE + 1):
            accounts = search_page(session, label_id, page)
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
                    'source': 'Apollo-account-export', 'notes': f"stage=Cold, label={label_name}",
                }

            state['done_pages'][label_id] = page
            if time.time() - last_flush > 30:
                save_cache(cache)
                save_state(state)
                last_flush = time.time()

            print(f"[{label_name}] page {page}: {len(accounts)} accounts "
                  f"(seen {total_seen}, new-to-cache {total_new})", flush=True)

            if len(accounts) < PER_PAGE:
                state['label_exhausted'][label_id] = True
                break
            time.sleep(SECONDS_BETWEEN_CALLS)
        else:
            print(f"WARNING: label '{label_name}' hit the 500-page cap even intersected with "
                  f"Cold - unexpected given label sizes seen earlier.")

        save_cache(cache)
        save_state(state)

    save_cache(cache)
    save_state(state)
    print(f"\nDone with all {len(labels)} label passes. {total_seen} account-rows seen "
          f"(with overlap vs prior passes), {total_new} net-new cache entries. "
          f"Cache now has {len(cache)} companies total.")


if __name__ == '__main__':
    main()
