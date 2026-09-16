"""
QA check: flags leads where the email domain doesn't plausibly match the
company name on file.

Why this exists: Apollo's /people/bulk_match (used in
01_apollo_bulk_lookup.py / 02_apollo_enrich_missing.py) is keyed by email and
returns whatever employer Apollo has on file for that person - it never
checks that employer's domain against the email's own domain. A stale Apollo
record can attach the wrong organization_name to a real email (e.g.
someone@whozoid.com tagged with organization_name "Saleshandy"), and nothing
downstream catches it before the lead reaches Smartlead/HeyReach.

This does NOT auto-correct anything - either the email or the company name
could be the wrong one, and company-name-to-domain matching is inherently
fuzzy (rebrands, multi-brand groups, product.io vs product.com). Flag for
manual review only, same philosophy as enrich_contacts_apollo.py's
domain_match_check.

Usage:
    python3 scripts/18_verify_domain_company_match.py <input_csv> [output_csv]
        [--email-col email] [--company-col organization_name]

If --company-col is omitted, the script looks for organization_name,
company_name, or company (in that order).

Adds one column, company_domain_match:
    OK                     - company name and email domain plausibly agree
    MISMATCH - ...         - needs manual review
    Generic email - ...    - gmail/yahoo/outlook/etc, can't verify against a company
    Skipped - ...          - missing email or company name
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _lazy import pd
from enrich_contacts_apollo import domain_root

GENERIC_EMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'icloud.com',
    'aol.com', 'proton.me', 'protonmail.com', 'live.com', 'msn.com',
}

# Business-type words that don't appear in a domain even when they're part
# of the legal/marketing name - stripped before comparing, not meant to be
# an exhaustive legal-suffix list (that's csv-normalizer's job).
_SUFFIX_RE = re.compile(
    r'\b(inc|incorporated|corp|corporation|ltd|limited|llc|llp|plc|co|company|'
    r'gmbh|pvt|private|pte|pty|group|holdings?|technologies|technology|tech|'
    r'solutions|labs|software)\b\.?',
    re.IGNORECASE,
)


def company_slug(name):
    """Best-effort company-name -> domain-root guess: lowercase, drop
    business-type words and punctuation. Not meant to be exact - just close
    enough to catch a domain that shares no root at all with the company
    name on file."""
    if not name:
        return ''
    slug = _SUFFIX_RE.sub('', str(name).lower())
    return re.sub(r'[^a-z0-9]', '', slug)


def check(email, company_name):
    if not email or '@' not in str(email):
        return 'Skipped - no email'
    if not company_name or not str(company_name).strip():
        return 'Skipped - no company name'

    domain = str(email).split('@')[-1].strip().lower()
    if not domain:
        return 'Skipped - no email domain'
    if domain in GENERIC_EMAIL_DOMAINS:
        return 'Generic email - cannot verify against company name'

    root = domain_root(domain)
    slug = company_slug(company_name)
    if not slug:
        return 'Skipped - no company name'

    if root == slug:
        return 'OK'
    if len(root) >= 4 and len(slug) >= 4 and (root in slug or slug in root):
        return 'OK (partial match)'
    return f'MISMATCH - email domain "{domain}" vs company "{company_name}" (needs manual review)'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input_csv')
    ap.add_argument('output_csv', nargs='?')
    ap.add_argument('--email-col', default='email')
    ap.add_argument('--company-col', default=None)
    args = ap.parse_args()

    df = pd.read_csv(args.input_csv)

    company_col = args.company_col
    if company_col is None:
        for candidate in ('organization_name', 'company_name', 'company'):
            if candidate in df.columns:
                company_col = candidate
                break
    if company_col is None or company_col not in df.columns:
        sys.exit(f"No company-name column found (tried organization_name/company_name/company). "
                  f"Pass --company-col explicitly. Columns: {list(df.columns)}")
    if args.email_col not in df.columns:
        sys.exit(f"Email column '{args.email_col}' not found. Columns: {list(df.columns)}")

    df['company_domain_match'] = [
        check(row[args.email_col], row[company_col]) for _, row in df.iterrows()
    ]

    output_csv = args.output_csv or args.input_csv.rsplit('.', 1)[0] + '_domain_checked.csv'
    df.to_csv(output_csv, index=False)

    counts = df['company_domain_match'].apply(lambda v: v.split(' - ')[0].split(' (')[0]).value_counts()
    print(f"\n{len(df)} rows checked -> {output_csv}")
    for label, n in counts.items():
        print(f"  {label}: {n}")

    mismatches = df[df['company_domain_match'].str.startswith('MISMATCH')]
    if len(mismatches):
        print(f"\n{len(mismatches)} mismatch(es) - review before sending:")
        for _, row in mismatches.iterrows():
            print(f"  {row[args.email_col]}  <->  {row[company_col]}")


if __name__ == '__main__':
    main()
