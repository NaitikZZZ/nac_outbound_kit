"""
Computes three deterministic GTM columns on a leads/accounts CSV that has
already been through the Apollo enrichment pipeline (needs a website/domain
column, and ideally a `technologies` column from enrich_full_fields_apollo.py):

  - competitor_match, competitor_name, competitor_threat, competitor_products:
      exact domain match against the attached Xoxoday competitor list
      (defaults to ~/Documents/Xoxoday/Xoxoday Competition(Final Competition
      list).csv - pass --competitors to point at a different copy).
  - dream_account: HubSpot domain lookup (cam_account == FY26CAM or
      is_fy_24_cam == true), reusing the same read-only signal as
      wrapper/backend/app/pipeline/dream_accounts.py. Never writes to HubSpot.
  - partner_tech_match: comma-separated Xoxoday partners found in the
      `technologies` column - matched against the REAL partner roster in
      HubSpot's custom "Partner" object (read-only, see hubspot_partner_list.py),
      not a hand-typed list. A small curated fallback list (FALLBACK_PARTNER_ALIASES
      below) supplements it for well-known integrations that show up in that
      object with incomplete status data.

These are deliberately NOT run through Apollo's AI Research field: matching
against a fixed list you already have is exact-match work, not a job for an
LLM doing live web search (which can't ingest your competitor CSV anyway and
risks hallucinated matches). See the "AI: Product to Pitch" etc. Apollo AI
field prompts drafted separately for the open-ended research columns.

Usage:
    python3 apollo_gtm_columns.py <input_csv> <output_csv> \
        [--competitors path/to/competitor_list.csv] \
        [--domain-col organization_website_url] [--tech-col technologies] \
        [--skip-dream-account]

Input CSV needs at least a domain/website column (default
'organization_website_url', matching enrich_full_fields_apollo.py's output;
pass --domain-col Domain if your file uses search_company_contacts_apollo.py's
naming instead). A `technologies` column is optional - partner_tech_match is
left blank per-row if it's missing.

This script only READS from HubSpot and only READS the competitor CSV - it
does not write anywhere. Pushing the three output columns back onto Apollo
account custom fields is a separate, not-yet-built step: it needs (a) the
three custom fields created in Apollo's UI first (Settings -> Manage Fields
-> Accounts) so you have their field IDs, and (b) one live --test call
verified against Apollo's current API before trusting it at scale - the same
"test one record, check nothing broke" discipline apollo_export_accounts_to_cache.py
already follows in this repo. Ask for that once you have the field IDs.
"""
import argparse
import csv
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from hubspot_dream_account_lookup import lookup_dream_accounts_by_domain  # noqa: E402
from hubspot_partner_list import fetch_partners  # noqa: E402

# Curated fallback for well-known global HRIS/collaboration integrations
# documented in reference/xoxoday-products.pdf. Kept alongside the live
# HubSpot Partner object (fetch_partners(), the real source of truth) because
# several of these show up in that object with a BLANK partner_status
# (confirmed live 2026-09-15 - BambooHR, Darwinbox, Keka, ADP, HiBob among
# them) even though the product docs confirm them as real integrations -
# likely stale CRM data entry, not evidence they aren't real partners.
FALLBACK_PARTNER_ALIASES = {
    'Workday': ['workday'],
    'SAP SuccessFactors': ['sap successfactors', 'successfactors'],
    'Oracle HCM': ['oracle hcm', 'oracle cloud hcm'],
    'Microsoft Teams': ['microsoft teams', 'ms teams'],
    'Slack': ['slack'],
    'Google Workspace': ['google workspace', 'gsuite', 'g suite'],
    'Microsoft Outlook': ['outlook', 'microsoft viva'],
    'Jira': ['jira'],
    'Zendesk': ['zendesk'],
}

_PAREN_RE = re.compile(r'\([^)]*\)')

# Excluded from tech-stack matching even though they're real HubSpot Partner
# records: confirmed live 2026-09-15 these are either unconfirmed/rejected
# relationships (partner_status), individual people rather than a tool a
# company's tech stack could ever name, or - the trickiest case - a real
# partner name that also happens to be an ordinary English word, which
# false-positive-matched constantly against unrelated tech-stack text (e.g.
# partner "ADA" (status: Prospect - never confirmed) matched the unrelated
# "Ada" chatbot product in a lead's stack; "ENGAGE" and "Remote" are
# common enough as generic words/other-vendors'-names that they aren't
# safe to auto-match regardless of status).
_EXCLUDED_STATUSES = {'Prospect', 'Denied/Terminated', 'Passive'}
_EXCLUDED_TYPES = {'Individual'}
_GENERIC_WORD_DENYLIST = {'engage', 'remote', 'ada'}


def _norm_alnum(text):
    return re.sub(r'[^a-z0-9]', '', (text or '').lower())


def build_partner_alias_map():
    """display_name -> {'aliases': [...], 'products': set(...)}. 'aliases' are
    normalized strings to match against technologies entries; 'products' is
    the union of each matching HubSpot record's `product_partner_interested`
    values (which Xoxoday product actually gets pitched through this partner
    relationship - a much stronger signal than guessing from tech-stack
    category alone). Combines the live HubSpot Partner object (source of
    truth, filtered per the exclusions above) with FALLBACK_PARTNER_ALIASES
    for names known to be real integrations despite incomplete HubSpot status
    data (see that constant's docstring) - those get no product association
    since they're not backed by a HubSpot record."""
    alias_map = {}
    seen_norms = {}  # normalized alias -> display name already used for it, to
    # dedupe e.g. separate "Workday" / "Workday (India)" HubSpot records that
    # both reduce to the same alias once the parenthetical is stripped.
    for p in fetch_partners():
        if p['type'] in _EXCLUDED_TYPES or p['status'] in _EXCLUDED_STATUSES:
            continue
        name = _PAREN_RE.sub('', p['name']).strip()  # "UKG (Vamsy)" -> "UKG"
        norm = _norm_alnum(name)
        if len(norm) < 3 or norm in _GENERIC_WORD_DENYLIST:
            continue
        display = seen_norms.setdefault(norm, name)
        entry = alias_map.setdefault(display, {'aliases': [], 'products': set()})
        entry['aliases'].append(norm)
        entry['products'].update(p['products'])
    for display, aliases in FALLBACK_PARTNER_ALIASES.items():
        entry = alias_map.setdefault(display, {'aliases': [], 'products': set()})
        entry['aliases'].extend(_norm_alnum(a) for a in aliases)
    return alias_map


def normalize_domain(value):
    if not value:
        return ''
    v = value.strip().lower()
    v = re.sub(r'^https?://', '', v)
    v = re.sub(r'^www\.', '', v)
    v = v.split('/')[0]
    return v.strip()


def load_competitors(path):
    """domain -> list of competitor rows (defends against duplicate domains)."""
    by_domain = {}
    with open(path, encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            domain = normalize_domain(row.get('Website', ''))
            if not domain:
                continue
            by_domain.setdefault(domain, []).append(row)
    return by_domain


_SHORT_ALIAS_LEN = 5  # aliases shorter than this must match a whole tech entry, not a substring


def match_partner_tech(tech_value, alias_map):
    """Matches per comma-separated tech ENTRY, not against the whole blob
    squashed together - squashing the full string first was matching short
    aliases inside unrelated words (e.g. "ADA" inside "Canada"/"Data" once
    spaces are stripped). Short aliases (<5 chars, e.g. "ADP", "TCS") must
    equal a whole entry exactly; longer aliases may substring-match within
    one entry (e.g. "Sales Force" -> "salesforce" inside "Salesforce CRM").

    Returns (matched_partner_names_str, suggested_products_str) - the second
    is the union of `product_partner_interested` across every matched
    partner, i.e. which Xoxoday product(s) actually get pitched through
    these specific partner relationships (a recorded GTM fact, not a guess)."""
    if not tech_value:
        return '', ''
    entries = [_norm_alnum(e) for e in tech_value.split(',') if e.strip()]
    if not entries:
        return '', ''
    matched = []
    products = set()
    for name, entry in alias_map.items():
        for alias in entry['aliases']:
            if len(alias) < _SHORT_ALIAS_LEN:
                hit = any(alias == e for e in entries)
            else:
                hit = any(alias in e for e in entries)
            if hit:
                matched.append(name)
                products.update(entry['products'])
                break
    return ', '.join(matched), ', '.join(sorted(products))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input_csv')
    ap.add_argument('output_csv')
    ap.add_argument('--competitors', default=os.path.expanduser(
        '~/Documents/Xoxoday/Xoxoday Competition(Final Competition list).csv'))
    ap.add_argument('--domain-col', default='organization_website_url')
    ap.add_argument('--tech-col', default='technologies')
    ap.add_argument('--skip-dream-account', action='store_true',
                     help='Skip the HubSpot lookup (e.g. no HUBSPOT_PRIVATE_APP_TOKEN set).')
    args = ap.parse_args()

    competitors = load_competitors(args.competitors)
    print(f"Loaded {sum(len(v) for v in competitors.values())} competitors "
          f"across {len(competitors)} unique domains from {args.competitors}")

    with open(args.input_csv, encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    if args.domain_col not in fieldnames:
        print(f"ERROR: column '{args.domain_col}' not found. Available columns: {fieldnames}", file=sys.stderr)
        sys.exit(1)

    domains = sorted({normalize_domain(r.get(args.domain_col, '')) for r in rows if r.get(args.domain_col)})
    dream_by_domain = {}
    if not args.skip_dream_account and domains:
        print(f"Looking up {len(domains)} domains against HubSpot dream-account fields (read-only)...")
        dream_by_domain = lookup_dream_accounts_by_domain(domains)

    print("Fetching Xoxoday's real partner list from HubSpot's Partner object (read-only)...")
    alias_map = build_partner_alias_map()
    print(f"  {len(alias_map)} partner names loaded for tech-stack matching")

    new_cols = ['competitor_match', 'competitor_name', 'competitor_threat',
                'competitor_products', 'dream_account', 'partner_tech_match',
                'partner_suggested_products']
    out_fieldnames = fieldnames + [c for c in new_cols if c not in fieldnames]

    matched_competitors = 0
    matched_dream = 0
    matched_partner_tech = 0

    for row in rows:
        domain = normalize_domain(row.get(args.domain_col, ''))
        comp_rows = competitors.get(domain, [])
        if comp_rows:
            matched_competitors += 1
            best = comp_rows[0]
            row['competitor_match'] = 'Yes'
            row['competitor_name'] = best.get('Name', '')
            row['competitor_threat'] = best.get('Threat', '')
            row['competitor_products'] = best.get('Products', '')
        else:
            row['competitor_match'] = 'No'
            row['competitor_name'] = ''
            row['competitor_threat'] = ''
            row['competitor_products'] = ''

        is_dream = dream_by_domain.get(domain, False)
        row['dream_account'] = 'Yes' if is_dream else 'No'
        if is_dream:
            matched_dream += 1

        tech_value = row.get(args.tech_col, '') if args.tech_col in fieldnames else ''
        partner_match, suggested_products = match_partner_tech(tech_value, alias_map)
        row['partner_tech_match'] = partner_match
        row['partner_suggested_products'] = suggested_products
        if partner_match:
            matched_partner_tech += 1

    with open(args.output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=out_fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} rows to {args.output_csv}")
    print(f"  competitor_match = Yes: {matched_competitors} ({matched_competitors * 100 // max(len(rows), 1)}%)")
    print(f"  dream_account = Yes:    {matched_dream} ({matched_dream * 100 // max(len(rows), 1)}%)")
    print(f"  partner_tech_match set: {matched_partner_tech} ({matched_partner_tech * 100 // max(len(rows), 1)}%)")


if __name__ == '__main__':
    main()
