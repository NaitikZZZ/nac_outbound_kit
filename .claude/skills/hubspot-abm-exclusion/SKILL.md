---
name: hubspot-abm-exclusion
description: Checks a prospect/lead CSV against the team's dynamic HubSpot "do not contact" list (list 28280, "ABM EXCLSIONS FINAL - DNU" in portal 6512810) and splits it into an OK-to-reach-out file and an excluded file with a reason per row. Matches on email, LinkedIn URL, company name (fuzzy), or a first name + last name + company combination. Use when the user wants to check a list against the exclusion list, dedupe against clients they don't want to reach out to, or asks "can I reach out to these people/companies".
---

# HubSpot dynamic ABM exclusion check

Cross-checks an outbound prospect list against Xoxoday's HubSpot list
**"ABM EXCLSIONS FINAL - DNU"** (list ID `28280`, portal `6512810`,
https://app-na2.hubspot.com/contacts/6512810/objectLists/28280/filters).
This is an **active/dynamic** HubSpot list — HubSpot itself keeps its
membership current based on its own filter criteria ("contacts with meetings
completed in the past year, linked to companies in specific categories and
deals at certain stages"). This skill keeps a local cache of that
membership and checks prospect lists against it.

This is a different exclusion source than the account-level
`abm-exclusion-check` skill (which checks the static Account Mapping Sheet
export for Dead/Growth client-relationship status). This skill matches at
the **contact** level, not just company/account level, and pulls its
source of truth live from HubSpot rather than a manually exported sheet.

## Two-part workflow

1. **Refresh the cache** (`scripts/refresh_cache.py`) — pulls the full list
   membership from HubSpot's REST API into `cache/exclusion_cache.csv`.
   Meant to run daily (e.g. via a cron job at 8am) so the cache never gets
   more than a day stale. Requires `HUBSPOT_API_KEY` in `.env` (see below).
2. **Check a prospect list** (`scripts/check_exclusions.py`) — matches an
   arbitrary lead/prospect CSV against the cache, no network calls needed.

## Setup

`.env` needs:

```
HUBSPOT_API_KEY=pat-...          # HubSpot Private App token, scopes: crm.objects.contacts.read, crm.lists.read
HUBSPOT_PORTAL_ID=6512810
HUBSPOT_EXCLUSION_LIST_ID=28280
```

`refresh_cache.py` calls HubSpot's public REST API directly (not the
MCP/chat HubSpot connector) because the list has 220k+ members — too large
to page through one MCP tool call at a time on an unattended daily
schedule. It needs real network access, so run it from a normal terminal,
not from a sandboxed environment without internet egress.

```bash
python3 .claude/skills/hubspot-abm-exclusion/scripts/refresh_cache.py
```

This writes `cache/exclusion_cache.csv` (raw contact fields) and
`cache/meta.json` (refresh timestamp + row count). Both are gitignored —
this is client PII and should never be committed.

### Daily 8am refresh

Installed as a cron job (confirmed with the user before installing, since
it's a standing schedule change):

```
0 8 * * * cd /Users/nac/ai-cold-email-campaign-kit && /usr/bin/python3 .claude/skills/hubspot-abm-exclusion/scripts/refresh_cache.py >> outputs/pipeline-log.md 2>&1
```

Check `crontab -l` to confirm it's still there, and `outputs/pipeline-log.md`
for its run output. The initial cache still needs one manual run (see
below) before the cron job has anything to build on top of.

## Running a check

```bash
python3 .claude/skills/hubspot-abm-exclusion/scripts/check_exclusions.py \
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
   confirmed with the user as the intended behavior.
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
was confirmed with the user as intentional (matches the conservative
approach in the sibling `abm-exclusion-check` skill: better to
under-prospect a whole account than risk contacting an active
relationship). If the user reports false positives from a generic/common
company name, that's this rule firing as designed — flag it to them rather
than silently loosening the fuzzy threshold.

## After running: presenting results

1. Report the summary counts from the summary file (total / excluded / OK,
   broken down by which rule fired).
2. Surface 3-5 example excluded rows with their reasons so the user can
   sanity-check before loading the OK list into Smartlead/HeyReach/
   Saleshandy.
3. If a large fraction excluded on company-name-alone matches, flag which
   companies are driving it (see "Top excluded companies" in the summary) —
   may indicate the cache is stale or a legitimately broad account
   exclusion.
4. Remind the user the cache has an age — check `cache/meta.json`'s
   `refreshed_at` and mention it if it's more than ~1 day old.
