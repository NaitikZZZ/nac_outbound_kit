---
name: hubspot-abm-exclusion
description: Checks a prospect/lead CSV against Xoxoday's dynamic HubSpot "do not contact" list ("ABM EXCLSIONS FINAL - DNU") and splits it into an OK-to-reach-out file and an excluded file with a reason per row. Matches on email, LinkedIn URL, company name (fuzzy), or a first name + last name + company combination. Use when the user wants to check a list against the exclusion list, dedupe against clients they don't want to reach out to, or asks "can I reach out to these people/companies".
---

# HubSpot dynamic ABM exclusion check

Cross-checks an outbound prospect list against Xoxoday's HubSpot list
**"ABM EXCLSIONS FINAL - DNU"**. This is an **active/dynamic** HubSpot
list — HubSpot itself keeps its membership current based on its own filter
criteria ("contacts with meetings completed in the past year, linked to
companies in specific categories and deals at certain stages"). This skill
keeps a local cache of that membership and checks prospect lists against
it.

This is a different exclusion source than a static Account Mapping Sheet
export (see `abm-exclusion-check` if/when that skill exists in this repo) —
that approach checks company/account-level Dead/Growth relationship status
from a manual export. This skill matches at the **contact** level and
pulls its source of truth live from HubSpot instead.

## Two-part workflow

1. **Refresh the cache** (`scripts/refresh_cache.py`) — pulls the full list
   membership from HubSpot's REST API into `cache/exclusion_cache.csv`.
   Meant to run daily (e.g. via a cron job) so the cache never gets more
   than a day stale. Requires `HUBSPOT_API_KEY` in `.env` (see below).
2. **Check a prospect list** (`scripts/check_exclusions.py`) — matches an
   arbitrary lead/prospect CSV against the cache, no network calls needed.

## Setup

`.env` needs (see `.env.example`):

```
HUBSPOT_API_KEY=pat-...          # HubSpot Private App token, scopes: crm.objects.contacts.read, crm.lists.read
HUBSPOT_PORTAL_ID=<your portal id>
HUBSPOT_EXCLUSION_LIST_ID=<the DNU list's id>
```

Find the list ID and portal ID from the list's HubSpot URL:
`https://app-na2.hubspot.com/contacts/{portal_id}/objectLists/{list_id}/filters`.

`refresh_cache.py` calls HubSpot's public REST API directly (not the
MCP/chat HubSpot connector) because this list is typically 200k+ members —
too large to page through one MCP tool call at a time on an unattended
daily schedule. It needs real network access, so run it from a normal
terminal, not from a sandboxed environment without internet egress. It's
resumable: progress checkpoints to `cache/_membership_ids.json` and
`cache/_partial_cache.csv`, so if the connection drops partway through
(likely, at this scale), just re-run it and it picks up where it left off
instead of starting over.

```bash
python3 skills/hubspot-abm-exclusion/scripts/refresh_cache.py
```

This writes `cache/exclusion_cache.csv` (raw contact fields) and
`cache/meta.json` (refresh timestamp + row count). The whole `cache/`
directory is gitignored — this is client PII and must never be committed.

### Daily refresh via cron

```bash
crontab -e
# add (adjust the repo path):
0 8 * * * cd /path/to/nac_outbound_kit && /usr/bin/python3 skills/hubspot-abm-exclusion/scripts/refresh_cache.py >> outputs/pipeline-log.md 2>&1
```

Confirm with whoever owns the machine before installing this — it's a
standing, persistent schedule change, not something to add silently.

## Running a check

```bash
python3 skills/hubspot-abm-exclusion/scripts/check_exclusions.py \
    --prospects /path/to/prospects.csv \
    --ok-out outputs/prospects-ok-to-reach.csv \
    --excluded-out outputs/prospects-excluded.csv \
    --summary-out outputs/prospects-exclusion-summary.md
```

`--cache` defaults to this skill's `cache/exclusion_cache.csv` — only pass
it explicitly to point at a different snapshot.

The script auto-detects common header names for email, company, LinkedIn
URL, and first/last name (or a single combined "Name" column, split on the
first space as a best-effort fallback). It prints what it detected to
stderr — check that before trusting the results if the CSV uses unusual
headers.

## Matching rules

A prospect is **excluded** if ANY of these match against the cache (a
prospect can match more than one rule — all firing reasons are recorded,
not just the first):

1. **Email** — exact match, case-insensitive.
2. **LinkedIn URL** — normalized (strip protocol/`www.`/query string/
   trailing slash) exact match against any of the cache's LinkedIn URL
   fields (`hs_linkedin_url`, `linkedin_url`, `pb_linkedin_profile_url`,
   `linkedin_personal_url` — HubSpot has several overlapping properties for
   this, so all are checked).
3. **Company name** — normalized (lowercase, punctuation collapsed, legal
   suffix like Inc/LLC/Pvt Ltd/Group stripped) exact match, falling back to
   fuzzy match at 88% similarity if no exact normalized match is found.
   This excludes **every** prospect at that company, not just one contact —
   intentional (see trade-off below).
4. **First name + last name + company** — an exact first+last name match
   in the cache, confirmed by at least one shared significant word between
   the prospect's and the cache contact's company names. Catches cases
   where the company field differs too much for rule 3's fuzzy threshold
   (e.g. "IDC" vs "International Data Corporation (IDC)") but the person is
   clearly the same.

If nothing matches, the prospect is OK to reach out.

## Known trade-off: company-alone matching is broad by design

Rule 3 means a single DNU contact at "Mastercard" excludes every prospect
whose company normalizes to "Mastercard" — not just that one person. This
is intentional: better to under-prospect a whole account than risk
contacting an active relationship. If you see false positives from a
generic/common company name, that's this rule firing as designed — flag it
rather than silently loosening the fuzzy threshold in `check_exclusions.py`.

## After running: presenting results

1. Report the summary counts from the summary file (total / excluded / OK,
   broken down by which rule fired).
2. Surface 3-5 example excluded rows with their reasons so you can
   sanity-check before loading the OK list into Smartlead/HeyReach/
   Saleshandy.
3. If a large fraction excluded on company-name-alone matches, check which
   companies are driving it (see "Top excluded companies" in the summary) —
   may indicate the cache is stale or a legitimately broad account
   exclusion.
4. Check the cache's age — `cache/meta.json`'s `refreshed_at` — and flag it
   if it's more than ~1 day old.
