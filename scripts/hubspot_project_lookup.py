"""
Look up a HubSpot Project record (portal 6512810, object type 0-970 /
"projects") and resolve its requestor + campaign owner to first names, for
the campaign naming convention's POC-name token and Project-ID suffix (see
docs/campaign-naming-convention.md).

Read-only (GET / search only, never writes/updates HubSpot - per this kit's
HubSpot rule). Uses HUBSPOT_PRIVATE_APP_TOKEN / HUBSPOT_API_KEY from .env,
which needs the crm.objects.owners.read scope (added 2026-09-11) in addition
to standard object read, since requestor/hubspot_owner_id are owner IDs that
need a separate lookup to become names.

Usage:
  python3 hubspot_project_lookup.py --id 684033751787
  python3 hubspot_project_lookup.py --search "ABM"
"""
import argparse
import json
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

HUBSPOT_TOKEN = os.environ.get('HUBSPOT_PRIVATE_APP_TOKEN') or os.environ.get('HUBSPOT_API_KEY')
BASE = 'https://api.hubapi.com/crm/v3/objects/projects'
PROPERTIES = ['hs_name', 'requestor', 'hubspot_owner_id', 'hs_status', 'hs_object_id']


def _headers():
    return {'Authorization': f'Bearer {HUBSPOT_TOKEN}', 'Content-Type': 'application/json'}


def get_by_id(project_id):
    r = requests.get(f'{BASE}/{project_id}', headers=_headers(),
                      params={'properties': ','.join(PROPERTIES)}, timeout=15)
    r.raise_for_status()
    return [r.json()]


def search_by_name(term, limit=10):
    r = requests.post(f'{BASE}/search', headers=_headers(),
                       json={'query': term, 'properties': PROPERTIES, 'limit': limit}, timeout=15)
    r.raise_for_status()
    return r.json().get('results', [])


def resolve_owner_first_name(owner_id):
    """Active and archived owners are mutually-exclusive filters on this
    endpoint - a former employee's owner record 404s without archived=true -
    so try both before giving up."""
    if not owner_id:
        return None
    for params in ({}, {'archived': 'true'}):
        r = requests.get(f'https://api.hubapi.com/crm/v3/owners/{owner_id}',
                          headers=_headers(), params=params, timeout=10)
        if r.status_code == 404:
            continue
        r.raise_for_status()
        first = (r.json().get('firstName') or '').strip()
        return first.title() if first else None
    return None


def main():
    if not HUBSPOT_TOKEN:
        sys.exit('Set HUBSPOT_PRIVATE_APP_TOKEN or HUBSPOT_API_KEY in .env')

    parser = argparse.ArgumentParser()
    parser.add_argument('--id', help='HubSpot Project record ID (exact)')
    parser.add_argument('--search', help='Text to search Project names for')
    parser.add_argument('--limit', type=int, default=10, help='Max results for --search (default 10)')
    args = parser.parse_args()

    if not args.id and not args.search:
        sys.exit('Pass --id <record_id> or --search "<project name>"')

    results = get_by_id(args.id) if args.id else search_by_name(args.search, args.limit)

    if not results:
        print('No matching Project records found.')
        return

    out = []
    for rec in results:
        props = rec.get('properties', {})
        out.append({
            'record_id': rec.get('id'),
            'name': props.get('hs_name'),
            'requestor_name': resolve_owner_first_name(props.get('requestor')),
            'campaign_owner_name': resolve_owner_first_name(props.get('hubspot_owner_id')),
            'status': props.get('hs_status'),
            'url': rec.get('url'),
        })

    print(json.dumps(out, indent=2))
    print(f'\n{len(out)} record(s). POC token = requestor_name + campaign_owner_name '
          f'(TitleCase, concatenated) + today\'s date; suffix = _<record_id>.')


if __name__ == '__main__':
    main()
