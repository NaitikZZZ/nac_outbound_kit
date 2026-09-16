"""
Read-only HubSpot lookup: which of a list of domains belong to a FY26 "dream
account" company. Never writes/updates HubSpot (Critical Rule #2).

Mirrors the exact same two signals as wrapper/backend/app/pipeline/
dream_accounts.py (that file lives inside the wrapper's FastAPI package and
uses relative imports, so it isn't directly importable from scripts/ - this
is a standalone copy of its logic, not a fork of its behavior):
  - cam_account (label "Dream Account Year"): counts as a 2026 dream account
    when it equals "FY26CAM".
  - is_fy_24_cam (label "Is Dream Account ?"): legacy Yes/No flag, kept as an
    additional signal since a company can be tagged on only one of the two.
is_dream_account_2026 = cam_account == "FY26CAM" OR is_fy_24_cam == "true".

Uses the HubSpot Search API with a domain IN filter (NOT batch/read with
idProperty="domain" - confirmed elsewhere in this repo that idProperty=domain
404s the entire batch call on this portal).
"""
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()
HUBSPOT_TOKEN = os.environ.get('HUBSPOT_PRIVATE_APP_TOKEN') or os.environ.get('HUBSPOT_API_KEY')

_SEARCH_CHUNK = 100
_DREAM_YEAR_VALUE = 'FY26CAM'
_MAX_RETRIES = 5


def _headers():
    return {'Authorization': f'Bearer {HUBSPOT_TOKEN}', 'Content-Type': 'application/json'}


def _search_page(chunk, after=None):
    body = {
        'filterGroups': [{'filters': [{'propertyName': 'domain', 'operator': 'IN', 'values': chunk}]}],
        'properties': ['domain', 'cam_account', 'is_fy_24_cam'],
        'limit': 100,
    }
    if after:
        body['after'] = after
    last_exc = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            r = requests.post('https://api.hubapi.com/crm/v3/objects/companies/search',
                               headers=_headers(), json=body, timeout=60)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            last_exc = e
            is_429 = getattr(e, 'response', None) is not None and e.response.status_code == 429
            time.sleep((30 if is_429 else 5) * attempt)
    raise last_exc


def lookup_dream_accounts_by_domain(domains):
    """domain (lowercased) -> True/False. A domain absent from HubSpot (no
    match) is treated as False - callers who need to distinguish "not a dream
    account" from "unknown company" should not rely on this shortcut."""
    if not HUBSPOT_TOKEN:
        print('  (no HUBSPOT_PRIVATE_APP_TOKEN/HUBSPOT_API_KEY set - skipping dream-account lookup, '
              'all rows will get dream_account=No)')
        return {}

    clean = sorted({str(d).strip().lower() for d in domains if d and str(d).strip()})
    out = {}
    for i in range(0, len(clean), _SEARCH_CHUNK):
        chunk = clean[i:i + _SEARCH_CHUNK]
        after = None
        while True:
            body = _search_page(chunk, after)
            for rec in body.get('results', []):
                props = rec.get('properties', {}) or {}
                domain = (props.get('domain') or '').strip().lower()
                if not domain:
                    continue
                cam = props.get('cam_account')
                legacy = (props.get('is_fy_24_cam') or '').strip().lower() == 'true'
                out[domain] = (cam == _DREAM_YEAR_VALUE) or legacy
            after = body.get('paging', {}).get('next', {}).get('after')
            if not after:
                break
    return out
