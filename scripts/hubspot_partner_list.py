"""
Read-only fetch of Xoxoday's real partner roster from HubSpot's custom
"Partner" object (objectTypeId 2-17592276, confirmed live 2026-09-15 via
GET /crm/v3/schemas). Never writes to HubSpot (Critical Rule #2).

This replaces guessing a partner list from reference/xoxoday-products.pdf -
the actual confirmed partner names, types, and statuses live here instead.
Caveat found live: the certified_compass/certified_empuls/certified_giift/
certified_plum fields exist on the schema but are unpopulated on every
record checked, and partner_status is blank on the majority of records
(184/295) - including some obviously-real global HRIS names (BambooHR,
Darwinbox, Keka, ADP, HiBob, Workday-adjacent entries) that show up in the
object but were never marked "Active". Treat "Active" as the reliable
positive signal, but don't assume a blank status means "not a partner" -
surface partner_status alongside the name so a human can judge.

Obvious test/demo records (names containing "test", "demo", "Epic Digital",
starting with "OLD -", etc.) are filtered out.
"""
import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()
HUBSPOT_TOKEN = os.environ.get('HUBSPOT_PRIVATE_APP_TOKEN') or os.environ.get('HUBSPOT_API_KEY')
PARTNER_OBJECT_TYPE_ID = '2-17592276'

_JUNK_PATTERNS = [
    re.compile(r'\btest\b', re.I), re.compile(r'\bdemo\b', re.I),
    re.compile(r'^epic digital', re.I), re.compile(r'^epic joanna', re.I),
    re.compile(r'^old\s*-', re.I),
]


def _headers():
    return {'Authorization': f'Bearer {HUBSPOT_TOKEN}'}


def _is_junk(name):
    return not name or any(p.search(name) for p in _JUNK_PATTERNS)


def fetch_partners():
    """Returns a list of {'name', 'type', 'status', 'products'} dicts, junk/test
    records filtered out. 'products' is the list of Xoxoday products this
    partner's `product_partner_interested` property names - HubSpot's own
    record of which Xoxoday product gets pitched through this partner
    relationship (confirmed live 2026-09-15: populated on 145/295 records).
    Paginates the full object (295 records as of 2026-09-15, well under
    HubSpot's per-object practical limits - no special handling needed for
    scale here)."""
    if not HUBSPOT_TOKEN:
        return []
    props = ['partner_name', 'partner_type', 'partner_status', 'product_partner_interested']
    out = []
    after = None
    while True:
        params = {'limit': 100, 'properties': ','.join(props)}
        if after:
            params['after'] = after
        r = requests.get(f'https://api.hubapi.com/crm/v3/objects/{PARTNER_OBJECT_TYPE_ID}',
                          headers=_headers(), params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        for rec in data.get('results', []):
            p = rec.get('properties', {})
            name = (p.get('partner_name') or '').strip()
            if _is_junk(name):
                continue
            products_raw = (p.get('product_partner_interested') or '').strip()
            products = [x.strip() for x in products_raw.split(';') if x.strip()] if products_raw else []
            out.append({'name': name, 'type': p.get('partner_type'), 'status': p.get('partner_status'),
                        'products': products})
        after = data.get('paging', {}).get('next', {}).get('after')
        if not after:
            break
    return out


if __name__ == '__main__':
    partners = fetch_partners()
    print(f"{len(partners)} partner records (junk/test filtered)")
    active = [p for p in partners if p['status'] == 'Active']
    print(f"{len(active)} marked Active")
    with_products = [p for p in partners if p['products']]
    print(f"{len(with_products)} have product_partner_interested set")
    for p in partners:
        print(f"  {p['name']:40s} | {p['type'] or '':30s} | {p['status'] or '(blank)':12s} | {', '.join(p['products'])}")
