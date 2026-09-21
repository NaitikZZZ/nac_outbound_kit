---
name: competitor-exclusion
description: Checks a prospect/lead CSV against Xoxoday's competitor list (reference/xoxoday-competitors.csv) and splits it into an OK-to-reach-out file and an excluded file with a reason per row. Matches on company name (fuzzy) or website/email domain. Use when the user wants to remove competitors from a lead list, or as the default Step 0 competitor-removal answer in the Standard Workflow (see CLAUDE.md).
---

# Competitor exclusion check

Cross-checks an outbound prospect list against Xoxoday's competitor list at
`reference/xoxoday-competitors.csv` (531 companies across Plum, Empuls, and
Loyalife's competitive set, with category, threat level, and notes per row).
This is a static reference file, not a live source — refresh it manually by
replacing `reference/xoxoday-competitors.csv` when the user hands over an
updated competitor list.

This is a different exclusion source than `hubspot-abm-exclusion` (HubSpot
DNU list — existing client/prospect relationships) and the account-level
`abm-exclusion-check` skill (Account Mapping Sheet). This one exists so
outbound campaigns don't accidentally pitch Plum/Empuls/Loyalife to a
company that competes with Xoxoday in that same space.

## Standing default (CLAUDE.md Step 0)

The Standard Workflow's Step 0 intake asks: **"Do you want to remove
competitors from your list?"** with a **default of yes**. If the user
doesn't answer or says yes, run this check before segmentation. If they
explicitly say no ("keep competitors in my list"), skip this skill entirely
for that campaign — don't run it silently.

## Running a check

```bash
python3 .claude/skills/competitor-exclusion/scripts/check_competitors.py \
    --prospects /path/to/prospects.csv \
    --ok-out outputs/<campaign-name>/prospects-ok-to-reach.csv \
    --excluded-out outputs/<campaign-name>/prospects-competitors-excluded.csv \
    --summary-out outputs/<campaign-name>/competitor-exclusion-summary.md
```

`--competitors` defaults to `reference/xoxoday-competitors.csv` — only pass
it explicitly to point at a different snapshot.

The script auto-detects common header names for company, website/domain,
and email (domain is derived from email if no website column exists). It
prints what it detected to stderr — check that before trusting the results
if the CSV uses unusual headers.

## Matching rules

A prospect is **excluded** if either matches (a prospect can match both;
all firing reasons are recorded):

1. **Website/email domain** — normalized (strip protocol/`www.`/path)
   exact match against a competitor's `Website` column.
2. **Company name** — normalized (lowercase, punctuation collapsed, legal
   suffix like Inc/LLC/Pvt Ltd stripped) exact match, falling back to fuzzy
   match at 88% similarity.

If nothing matches, the prospect is OK to reach out.

## After running: presenting results

1. Report the summary counts (total / excluded / OK, broken down by match
   type) from the summary file.
2. Surface 3-5 example excluded rows with the competitor name, category,
   and threat level so the user can sanity-check before loading the OK list
   into Smartlead/HeyReach/Saleshandy.
3. If a large fraction excluded on a fuzzy company match, flag it — a
   common/generic company name can trip the 88% threshold on an unrelated
   business.
