"""
Apollo Account-level custom field IDs for the GTM columns computed by
apollo_gtm_columns.py. Created live in Apollo's UI (Settings -> this
workspace's Companies/Accounts table -> Add column -> Create field) on
2026-09-15, confirmed via GET https://api.apollo.io/api/v1/typed_custom_fields.

If these fields are ever renamed or recreated, re-fetch their IDs with:
    python3 -c "
    import os, requests
    from dotenv import load_dotenv; load_dotenv()
    r = requests.get('https://api.apollo.io/api/v1/typed_custom_fields',
                      headers={'x-api-key': os.environ['APOLLO_API_KEY']})
    for f in r.json()['typed_custom_fields']:
        if f['modality'] == 'account':
            print(f['id'], f['name'], f['type'])
    "
"""

# Single-line text fields - value is a plain string.
COMPETITOR_NAME_FIELD_ID = '6aa94390b3222c000c1e94e6'
COMPETITOR_THREAT_FIELD_ID = '6aa943a8d349b3001c0684d1'
COMPETITOR_PRODUCTS_FIELD_ID = '6aa943b77438f8001c835ac2'

# Multi-line text field - value is a plain string.
PARTNER_TECH_MATCH_FIELD_ID = '6aa943d94302e8002080525b'

# Single-select picklist fields - value must be a list containing the
# picklist OPTION id (not the display text), e.g. [COMPETITOR_MATCH_YES_ID].
COMPETITOR_MATCH_FIELD_ID = '6aa94370d89f9500147be65b'
COMPETITOR_MATCH_YES_ID = '6aa94370d89f9500147be659'
COMPETITOR_MATCH_NO_ID = '6aa94370d89f9500147be65a'

DREAM_ACCOUNT_FIELD_ID = '6aa943c5d44244000c33ddc0'
DREAM_ACCOUNT_YES_ID = '6aa943c5d44244000c33ddbe'
DREAM_ACCOUNT_NO_ID = '6aa943c5d44244000c33ddbf'


def build_typed_custom_fields(row):
    """row is one output row from apollo_gtm_columns.py (has competitor_match,
    competitor_name, competitor_threat, competitor_products, dream_account,
    partner_tech_match keys). Returns the typed_custom_fields payload dict
    ready to PUT to /api/v1/accounts/{id}."""
    is_competitor = (row.get('competitor_match') or '').strip().lower() == 'yes'
    is_dream = (row.get('dream_account') or '').strip().lower() == 'yes'
    return {
        COMPETITOR_MATCH_FIELD_ID: [COMPETITOR_MATCH_YES_ID if is_competitor else COMPETITOR_MATCH_NO_ID],
        COMPETITOR_NAME_FIELD_ID: row.get('competitor_name', '') or '',
        COMPETITOR_THREAT_FIELD_ID: row.get('competitor_threat', '') or '',
        COMPETITOR_PRODUCTS_FIELD_ID: row.get('competitor_products', '') or '',
        DREAM_ACCOUNT_FIELD_ID: [DREAM_ACCOUNT_YES_ID if is_dream else DREAM_ACCOUNT_NO_ID],
        PARTNER_TECH_MATCH_FIELD_ID: row.get('partner_tech_match', '') or '',
    }
