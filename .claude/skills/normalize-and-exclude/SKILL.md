---
name: normalize-and-exclude
description: One-pass pipeline for a raw outbound CSV -- cleans it with csv-normalizer, then checks the cleaned list against the HubSpot ABM exclusion cache, and lands two files: one OK to reach out, one excluded with a reason per row. Use when the user hands over a fresh lead/prospect list and wants it ready to load into Smartlead/HeyReach/Saleshandy in one go, or says things like "clean and check this list" or "get this ready to send."
---

# Normalize + exclude pipeline

Wires together two existing skills -- [csv-normalizer](../csv-normalizer/SKILL.md)
and [hubspot-abm-exclusion](../hubspot-abm-exclusion/SKILL.md) -- into a single
command. No logic lives here; it just calls both scripts in order so a raw CSV
in becomes two ready-to-use files out.

## Running it

```bash
python3 .claude/skills/normalize-and-exclude/scripts/run_pipeline.py \
    --in path/to/raw-leads.csv \
    --stem outputs/leads
```

Produces:

| File | What it is |
| --- | --- |
| `outputs/leads-clean.csv` | Normalized CSV with `Cleaned <X>` columns |
| `outputs/leads-normalization-report.md` | Normalizer's QA report + flag histogram |
| `outputs/leads-ok-to-reach-out.csv` | Cleaned prospects NOT on the exclusion list |
| `outputs/leads-excluded.csv` | Cleaned prospects on the exclusion list, with reason(s) |
| `outputs/leads-exclusion-summary.md` | Counts by exclusion rule |

Pass `--strip-the` / `--strip-tagline` / `--strip-geo` to forward those flags
to the normalizer. Pass `--cache <path>` only to point at a non-default
exclusion cache snapshot.

## Before running

- Check `.claude/skills/hubspot-abm-exclusion/cache/meta.json`'s
  `refreshed_at`. If it's more than ~1 day old, mention that to the user --
  the exclusion check runs against whatever is cached, not live HubSpot data.
- Do the raw CSV inspection step from csv-normalizer first (`head -3`, `wc -l`)
  if the headers or delimiter look unusual -- the pipeline doesn't do that for
  you.

## After running

Follow both skills' own "present results" guidance:
- Report normalization flag counts from the normalization report; open flagged
  rows before treating `-clean.csv` as final.
- Report the exclusion summary counts and 3-5 example excluded rows with
  reasons, per hubspot-abm-exclusion's instructions, before the user loads
  `-ok-to-reach-out.csv` into their sending tool.

## Scope

This is normalize + exclude only. It does not enrich missing data (company
website, LinkedIn URL, verified email) -- that's a separate, not-yet-built
enrichment step for a CSV that only has partial columns (company name only,
name only, LinkedIn URL only, etc.). Don't fold enrichment logic in here when
that gets built; it's a distinct stage that runs before normalization, not
inside this script.
