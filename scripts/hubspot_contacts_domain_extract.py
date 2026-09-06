"""
Derives company -> domain mappings from the HubSpot exclusion-list contact
cache (.claude/skills/hubspot-abm-exclusion/cache/exclusion_cache.csv) and
merges them into the shared reference/company_domain_cache.csv.

Why this exists: the live HubSpot Company-search domain-resolution tier
(hubspot_resolve() in resolve_company_domains.py) is currently blocked - the
configured private-app token lacks the crm.objects.companies.read scope
(confirmed live: 403 MISSING_SCOPES). The exclusion cache was already built
via a different, working code path (crm/v3/lists/.../memberships +
crm/v3/objects/contacts/batch/read, a CONTACTS read, different scope) and
sits on disk already - checked live: its 'company_domain' column is 100%
blank across all 222,962 rows (not just a sampling fluke), but 'email' is
populated for 222,193 of them. A contact's work-email domain IS their
company's domain, so this recovers real domain data with zero new API
calls, zero scope issues, zero rate limits - purely local file processing.

Per company (grouped by the same norm() used everywhere else in this repo):
take the most common non-generic email domain among its contacts. A company
with 5 contacts all at @philips.com is confident; one whose contacts split
across genuinely different domains with no clear majority is flagged rather
than guessed, matching the majority-wins-or-flag philosophy already used for
Apollo's multi-candidate disambiguation in resolve_company_domains.py.

Usage: python3 hubspot_contacts_domain_extract.py
"""
import os
import sys
import csv
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from resolve_company_domains import load_cache, save_cache, norm  # noqa: E402

EXCLUSION_CACHE_PATH = os.path.join(
    os.path.dirname(__file__), '..', '.claude', 'skills', 'hubspot-abm-exclusion', 'cache', 'exclusion_cache.csv'
)

# Personal/free email providers - never a company's own domain, so any hit
# here is discarded rather than treated as a real (wrong) company domain.
GENERIC_EMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'yahoo.co.in', 'ymail.com', 'rocketmail.com',
    'outlook.com', 'hotmail.com', 'live.com', 'msn.com',
    'icloud.com', 'me.com', 'mac.com',
    'aol.com', 'protonmail.com', 'proton.me', 'zoho.com',
    'rediffmail.com', 'indiatimes.com', 'in.com',
}

# A company is only trusted if its top domain has a real majority among its
# contacts, not just a plurality - e.g. 3 contacts split 1/1/1 across three
# domains has no majority and should flag, not silently pick one of three.
MIN_MAJORITY_FRACTION = 0.5


def load_company_email_domains():
    company_domains = defaultdict(Counter)
    company_display_name = {}
    total_rows = 0
    with open(EXCLUSION_CACHE_PATH, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            total_rows += 1
            company_raw = (row.get('company') or '').strip()
            email = (row.get('email') or '').strip().lower()
            if not company_raw or not email or '@' not in email:
                continue
            domain = email.split('@')[-1].strip()
            if not domain or '.' not in domain or domain in GENERIC_EMAIL_DOMAINS:
                continue
            key = norm(company_raw)
            if not key:
                continue
            company_domains[key][domain] += 1
            company_display_name.setdefault(key, company_raw)
    return total_rows, company_domains, company_display_name


def main():
    total_rows, company_domains, company_display_name = load_company_email_domains()
    print(f"{total_rows} contact rows scanned, {len(company_domains)} distinct companies with a usable email domain.")

    cache = load_cache()
    resolved, ambiguous, already_cached, new_entries = 0, 0, 0, 0

    for key, domain_counts in company_domains.items():
        if key in cache:
            already_cached += 1
            continue

        total = sum(domain_counts.values())
        top_domain, top_count = domain_counts.most_common(1)[0]

        if top_count / total < MIN_MAJORITY_FRACTION and len(domain_counts) > 1:
            ambiguous += 1
            continue

        resolved += 1
        cache[key] = {
            'company_key': key, 'company_name': company_display_name[key], 'domain': top_domain,
            'linkedin': '', 'country': '', 'city': '',
            'source': 'HubSpot-contact-email-derived',
            'notes': f"{top_count}/{total} contacts at this domain",
        }
        new_entries += 1

    save_cache(cache)
    print(f"\n{resolved} companies resolved from contact emails, {ambiguous} flagged as ambiguous "
          f"(no clear majority domain), {already_cached} already in cache. "
          f"{new_entries} new cache entries saved. Cache now has {len(cache)} companies total.")


if __name__ == '__main__':
    main()
