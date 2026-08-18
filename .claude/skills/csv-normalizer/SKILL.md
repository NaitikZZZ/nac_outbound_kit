---
name: csv-normalizer
description: Normalize a CSV or spreadsheet of leads for outbound. Splits Full Name into First/Last while keeping Full Name, strips legal suffixes and "a company of X" descriptors from company names, fixes casing (ALL CAPS and all lowercase), normalizes whitespace, and standardizes city/state/country. Phone numbers are left completely untouched by design. Use when the user shares a lead, prospect, contact, or ABM list and asks to clean, normalize, standardize, tidy, or fix the formatting of it, or mentions messy casing, legal suffixes, split names, or inconsistent locations.
---

# CSV normalizer

Cleans an outbound list so merge tags render as a human would write them.
`{{Company}}` should produce `Panamax`, not `PANAMAX INC.`.

## Non-negotiables

1. **Never overwrite a source column.** Every output goes to a new `Cleaned <X>`
   column. The raw value stays for audit and rollback.
2. **Row count in must equal row count out.** No dropping, no dedupe, no
   reordering. Cleaning and filtering are separate jobs.
3. **Never invent data.** A blank stays blank. Uncertain becomes a flag, not a guess.
4. **Flag, don't silently fix.** Anything ambiguous lands in `Normalization Flags`
   for a human pass.
5. **Preserve diacritics and non-Latin scripts.** `José`, `Nestlé`, `São Paulo`,
   `Søren` keep their characters. Never transliterate to ASCII.

## Procedure

### 1. Inspect before touching anything

```bash
head -3 <file.csv> && wc -l <file.csv>
```

Confirm: real header row (Apollo and Clay exports sometimes carry title/preamble
rows above it), delimiter, and which columns hold names, company, location.

### 2. Run the script

```bash
python3 .claude/skills/csv-normalizer/scripts/normalize.py --in leads.csv --out outputs/leads-clean.csv --report outputs/normalization-report.md
```

Stdlib only, no dependencies. Flags:

| Flag | Effect | Default |
| --- | --- | --- |
| `--strip-the` | `The Trade Desk` becomes `Trade Desk` | off |
| `--strip-tagline` | `Stripe \| Payments Infra` becomes `Stripe` | off |
| `--strip-geo` | `Acme (US)` becomes `Acme` | off |

There is no country default and no country inference anywhere. Everything the
script writes is derived from the cell it read.

### 3. Read the report, then review the flags

The report prints detected columns, cells rewritten, and a flag histogram. Open
the flagged rows and fix by hand or by LLM pass. Priority order:

- `formula_injection_blocked` — the cell was a spreadsheet formula, not a name
- `placeholder_first_name` — `Hi`, `There`, `Team`, `Info`; do not mail merge these
- `company_empty_after_clean` — cleaning consumed the whole value
- `suffix_is_whole_name_kept` — the legal suffix *was* the name (`The Limited`)
- `derived_from_domain` — company column held a bare domain
- `country_unmapped` / `state_unmapped` — extend the lookup tables in the script

`mononym` and `legal_suffix_removed` are informational and usually need no action.

## Phone numbers are not touched

By design. The script does not detect a phone column, add a cleaned phone
column, or reformat anything in one. Whatever is in that column — raw, later
enriched, in any format — passes straight through byte-for-byte. Any
reformatting, splitting into a country code, or E.164 conversion is a separate
job the user hasn't asked for and shouldn't be inferred: a wrong guess there
produces a number that dials the wrong country, which is worse than leaving it
alone.

### 4. Verify before shipping

```bash
python3 -c "import csv;a=len(list(csv.DictReader(open('leads.csv',encoding='utf-8-sig'))));b=len(list(csv.DictReader(open('outputs/leads-clean.csv',encoding='utf-8-sig'))));print(a,b,'MATCH' if a==b else 'MISMATCH')"
```

Then eyeball 10 rows of `Cleaned Company` and `Cleaned First Name` in a merge-tag
sentence: "Hi {{First Name}}, I noticed {{Company}} recently ...". If any row reads
wrong out loud, fix that row and add the pattern to the script.

## Name splitting

`First Name` is the first token. `Last Name` is everything after it, so middle
names, initials, and particles stay with the surname. `Full Name` is always kept.

| Input | Full | First | Last |
| --- | --- | --- | --- |
| `Dr. JANE Q. DOE PhD` | Jane Q. Doe | Jane | Q. Doe |
| `Smith, John` | John Smith | John | Smith |
| `van der berg, klaas` | Klaas van der Berg | Klaas | van der Berg |
| `JOSÉ MARÍA GARCÍA LÓPEZ` | José María García López | José | María García López |
| `Madonna` | Madonna | Madonna | *(blank)* |

The middle-into-last rule matters for Spanish, Portuguese, and Dutch names where
the surname is genuinely multi-token. It costs nothing for outbound, which only
merges `First Name`.

## Casing rule

Re-case only strings that are uniformly cased. `MARCUS AND MILLICHAP` and
`acme corp` get fixed. `iPhone`, `eBay`, `LinkedIn`, and `McKinsey` are already
mixed-case, which is a deliberate signal, so they are left alone.

Within an ALL-CAPS source, short tokens that are not ordinary English words are
kept uppercase as acronyms: `FMFE, CPA, P.C.` becomes `FMFE, CPA`, while
`OLD WORLD INDUSTRIES` becomes `Old World Industries`.

## Location resolution order

When a row has both a `Location` free-text column and a dedicated `Country`
column, `Country` wins for the country, but `Location` still gets parsed for
city and state — it is not skipped just because `Country` is filled. That
matters for the `CA` collision: `San Francisco, CA` with `Country = USA`
resolves `CA` as California, not Canada, because a real country is already
known. Without a trustworthy Country column, a lone `CA` is genuinely
ambiguous and the same string could mean either.

## Full edge-case catalog

`reference/edge-cases.md` lists every case the script handles, what it does, and
the ones it deliberately punts to a flag. Read it before extending the script or
hand-fixing a batch.

`reference/prompt.md` is a standalone prompt for normalizing a small pasted list
or for running this logic somewhere without Python (Clay AI column, ChatGPT, a
Claude project). Under about 200 rows, prefer the script anyway: it is
deterministic and repeatable, and an LLM will quietly drop rows on long lists.

## Extending

All vocabulary lives in module-level constants at the top of `normalize.py`:
`LEGAL_SUFFIXES`, `BRAND_CASE`, `ACRONYMS`, `HONORIFICS`, `NAME_SUFFIXES`,
`COUNTRY_CANON`, `CITY_CANON`, `NON_LOCATIONS`, `COLUMN_ALIASES`. Add entries
there rather than writing new regexes. After any edit, re-run against
`outputs/apollo-contacts-okay-to-reach-out.csv` and diff the flag histogram.
