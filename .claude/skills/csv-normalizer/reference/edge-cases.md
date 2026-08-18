# Normalization edge cases

Every case below is either handled by `scripts/normalize.py` or deliberately
flagged for a human. **Handled** means deterministic. **Flag** means the script
refuses to guess and writes a marker into `Normalization Flags`.

---

## 1. File level

| # | Case | Example | Behavior |
| --- | --- | --- | --- |
| 1.1 | UTF-8 BOM | `﻿First Name` | Handled, stripped |
| 1.2 | cp1252 / latin-1 file | bytes fail UTF-8 decode | Handled, charset sniffed |
| 1.3 | Mojibake already in text | `Ã©` for `é`, `â€™` for `'` | Handled, round-tripped back |
| 1.4 | Semicolon delimiter (EU Excel) | `name;company;email` | Handled, sniffed |
| 1.5 | Tab or pipe delimiter | `.tsv` saved as `.csv` | Handled, sniffed |
| 1.6 | Preamble rows above the header | Clay/ABM exports with a title row | Handled, first plausible header row wins |
| 1.7 | Duplicate header names | two `Email` columns | Handled, renamed `Email (1)` |
| 1.8 | Blank / unnamed columns | `,,,` | Handled, named `Column 4` |
| 1.9 | Ragged rows | row has 12 fields, header has 14 | Handled, padded, counted in report |
| 1.10 | Embedded commas, quotes, newlines in a quoted field | `"Acme, Inc."` | Handled by the csv module |
| 1.11 | CRLF vs LF vs bare CR | mixed line endings | Handled |
| 1.12 | Formula injection on output | cell starts `=`, `+`, `-`, `@` | Handled, prefixed with `'` so Excel cannot execute it |
| 1.13 | Formula in a name cell | `=cmd\|'/c calc'!A1` | **Flag** `formula_injection_blocked`, cleaned name left blank |
| 1.14 | Column name variants | `first_name`, `First Name`, `FNAME`, `Given Name` | Handled, alias table |
| 1.15 | Empty file / no data rows | | Hard error, exits |
| 1.16 | Row count drift | | Asserted equal in the verify step |

---

## 2. Person names

### Structure

| # | Case | Example | Result |
| --- | --- | --- | --- |
| 2.1 | Plain two-token | `John Smith` | John / Smith |
| 2.2 | Middle name | `John Quincy Smith` | John / Quincy Smith |
| 2.3 | Middle initial | `Jane Q. Doe` | Jane / Q. Doe |
| 2.4 | Comma-inverted | `Smith, John` | John / Smith, flag `name_uninverted` |
| 2.5 | Inverted with credentials | `Smith, John, MBA` | Not un-inverted (tail is a credential), suffix stripped |
| 2.6 | Mononym | `Madonna`, `Prakash` | First only, **flag** `mononym` |
| 2.7 | Four-plus tokens | `José María García López` | José / María García López, **flag** `name_unusually_long` past 4 |
| 2.8 | Full name sitting in the First Name column | `First Name = "John Smith"`, Last blank | **Flag** `full_name_in_first_name_column`, split anyway |
| 2.9 | Only First + Last, no Full | | Full Name synthesized from both |
| 2.10 | Explicit Last Name column disagrees with the split | | Explicit value wins if it appears in the full name |

### Noise to strip

| # | Case | Example | Result |
| --- | --- | --- | --- |
| 2.11 | Honorific prefix | `Dr.`, `Mr`, `Prof`, `Shri`, `Adv`, `Capt`, `Er` | Removed |
| 2.12 | Generational suffix | `Jr`, `Sr`, `III`, `IV` | Removed, **flag** `suffix_removed:III` |
| 2.13 | Credential suffix | `PhD`, `MBA`, `CPA`, `Esq`, `PMP`, `CFA` | Removed |
| 2.14 | Credential soup | `Jane Doe, MBA, PMP, CSM` | All removed |
| 2.15 | Pronouns | `(she/her)`, `he/him`, `[they/them]` | Removed |
| 2.16 | Emoji | `John Smith 🚀✅` | Removed |
| 2.17 | LinkedIn banner | `John Smith \| Open to Work`, `— We're Hiring!` | Removed |
| 2.18 | Nickname in quotes or parens | `John "Jack" Smith` | Formal name kept, **flag** `nickname_removed:Jack` |
| 2.19 | Job title appended | `John Smith, CEO` | Comma tail dropped |
| 2.20 | URL in the field | `John Smith linkedin.com/in/js` | Stripped, **flag** `name_contains_url` |
| 2.21 | Email in the field | `john.smith@acme.com` | **Flag** `name_looks_like_email`, no name derived |
| 2.22 | Placeholder | `Hi`, `There`, `Team`, `Info`, `Sales` | **Flag** `placeholder_first_name` — never mail-merge these |
| 2.23 | Nullish | `N/A`, `-`, `unknown`, `NULL`, `#N/A` | Blank |

### Casing

| # | Case | Example | Result |
| --- | --- | --- | --- |
| 2.24 | ALL CAPS | `JOHN SMITH` | John Smith |
| 2.25 | all lowercase | `john smith` | John Smith |
| 2.26 | Already mixed case | `McKinsey`, `DeAndre` | Left untouched, mixed case is intentional |
| 2.27 | Hyphenated | `mary-jane` | Mary-Jane |
| 2.28 | Apostrophe | `o'brien`, `d'angelo` | O'Brien, D'Angelo |
| 2.29 | `Mc` prefix | `mcdonald` | McDonald (needs 3+ following letters) |
| 2.30 | `Mac` prefix | `macdonald`, `machado` | **Not touched** — `Macey` and `Mackenzie` would break |
| 2.31 | Dutch/German/Spanish particles | `van der berg`, `von neumann`, `de la cruz` | Particles stay lowercase: `van der Berg` |
| 2.32 | Particle leading the whole name | `Van Damme` as First | Lowercased to `van`; **known limitation**, check flagged rows |
| 2.33 | Initials with periods | `j.r.r. tolkien` | J.R.R. Tolkien |
| 2.34 | Diacritics | `josé`, `søren`, `zoë` | Preserved, never transliterated |
| 2.35 | Non-Latin script | `田中太郎`, `राहुल` | Left as-is, no case logic applied |
| 2.36 | Smart apostrophe | `O’Brien` | Normalized to straight `'` |

---

## 3. Company names

### Legal suffixes

| # | Case | Example | Result |
| --- | --- | --- | --- |
| 3.1 | Anglo suffixes | `Inc`, `Inc.`, `Incorporated`, `Corp`, `Ltd`, `Limited`, `LLC`, `L.L.C.`, `LLP`, `PLC`, `Co`, `Company` | Stripped |
| 3.2 | Trailing period after suffix | `Reyes Holdings, L.l.c.` | Stripped |
| 3.3 | Stacked suffixes | `Acme Holdings Pvt. Ltd. Co.` | All stripped, up to 4 passes |
| 3.4 | Indian | `Pvt Ltd`, `Pvt. Ltd.`, `Private Limited` | Stripped |
| 3.5 | Singapore / Malaysia / Australia | `Pte Ltd`, `Sdn Bhd`, `Pty Ltd` | Stripped |
| 3.6 | German / Dutch / Nordic | `GmbH`, `AG`, `BV`, `NV`, `AB`, `A/S`, `ApS`, `Oy` | Stripped |
| 3.7 | Romance | `S.A.`, `SAS`, `SARL`, `SRL`, `SpA`, `Ltda`, `S.A. de C.V.` | Stripped |
| 3.8 | Asian | `K.K.`, `Co., Ltd.`, `PT`, `Tbk` | Stripped |
| 3.9 | Slavic | `Sp. z o.o.`, `d.o.o.`, `s.r.o.`, `OOO`, `JSC` | Stripped |
| 3.10 | Gulf | `FZCO`, `FZE`, `DMCC`, `WLL`, `QSC` | Stripped |
| 3.11 | **Suffix is the entire name** | `The Limited`, `Company`, `121 Corp` | **Kept whole**, flag `suffix_is_whole_name_kept` |
| 3.12 | Suffix word mid-name | `Limited Brands`, `Corporate Express` | Not stripped, only trailing position matches |
| 3.13 | `Unlimited Company` | `LinkedIn Ireland Unlimited Company` | Only `Company` strips: `LinkedIn Ireland Unlimited` |
| 3.14 | `& Company` | `Sb & Company`, `Smith & Company` | Stripped. **Judgment call** — turn this off if the firm brands on it |

### Descriptor clauses

| # | Case | Example | Result |
| --- | --- | --- | --- |
| 3.15 | `, a company of X` | `Cora, a company of Blank` | `Cora` |
| 3.16 | `, an X Company` | `Audible, an Amazon Company` | `Audible` |
| 3.17 | Portfolio-company phrasing | `LivCor, a Blackstone Portfolio Company` | `LivCor` |
| 3.18 | `- A X Company` | `Spectrum Science - A Ghmc Company` | `Spectrum Science` |
| 3.19 | `(formerly X)` | `Grow America (formerly NDC)` | `Grow America` |
| 3.20 | `dba` / `fka` | `Acme Corp dba Widgets` | `Acme Corp` then suffix strip |
| 3.21 | `, part of X` / `, a division of X` / `, acquired by X` | | Tail dropped |
| 3.22 | Appositive that is not a descriptor | `Avant, The Language Proficiency Company` | Tail dropped — correct here, but verify on flagged rows |

### Casing and formatting

| # | Case | Example | Result |
| --- | --- | --- | --- |
| 3.23 | ALL CAPS | `IDEAL INDUSTRIES` | Ideal Industries |
| 3.24 | ALL CAPS containing an acronym | `FMFE, CPA, P.C.` | `FMFE, CPA` — short non-word tokens stay uppercase |
| 3.25 | ALL CAPS ordinary short word | `OLD WORLD INDUSTRIES` | Old World Industries |
| 3.26 | Alphanumeric acronym | `D4C DENTAL BRANDS` | D4C Dental Brands |
| 3.27 | Known acronym in any case | `ibm`, `kpmg`, `pwc`, `at&t` | IBM, KPMG, PwC, AT&T |
| 3.28 | Brand casing | `linkedin`, `ebay`, `hubspot`, `openai`, `byjus` | LinkedIn, eBay, HubSpot, OpenAI, BYJU'S |
| 3.29 | Already mixed case | `iPhone`, `dbt Labs`, `n8n` | Untouched |
| 3.30 | `and` between capitals | `Marcus and Millichap` | `Marcus & Millichap` |
| 3.31 | `and` not between capitals | `Wine and dine` | Left alone |
| 3.32 | Ampersand spacing | `Company&Associates`, `A  &  B` | `Company & Associates`, `A & B` |
| 3.33 | Internal stopwords | `BANK OF THE WEST` | `Bank of the West` |
| 3.34 | HTML entity | `Johnson &amp; Johnson` | `Johnson & Johnson` |
| 3.35 | Emoji / trademark glyph | `Acme 🚀`, `Acme™` | Removed |
| 3.36 | Wrapping quotes | `"Acme Inc"` | Unwrapped |
| 3.37 | Leading `The` | `The Home Depot` | **Kept** by default. `--strip-the` opts in |
| 3.38 | Marketing tagline | `Stripe \| Payments Infrastructure` | **Kept** by default. `--strip-tagline` opts in |
| 3.39 | Geographic parenthetical | `Acme (US)`, `Acme (EMEA)` | **Kept** by default. `--strip-geo` opts in |
| 3.40 | Quality marker, bracketed | `Acme (DUPE)`, `Firm [TEST]` | Removed |
| 3.41 | Quality marker, trailing | `Acme - DO NOT USE` | Removed |
| 3.42 | Marker word that is really part of the name | `Old Dominion University`, `Avalon Test Equipment` | **Preserved.** Bare mid-name matches are never stripped |
| 3.43 | Bare domain in the company column | `acme-widgets.com`, `Tns.org` | `Acme Widgets`, `Tns`, **flag** `derived_from_domain` — verify these |
| 3.44 | Diacritics | `Nestlé S.A.` | `Nestlé` |
| 3.45 | Very long value | over 60 chars | **Flag** `company_unusually_long`, often a tagline or a description |
| 3.46 | Non-Latin script | `株式会社エイコー` | Left as-is |
| 3.47 | Suffix-only remainder | cleaning would empty the cell | Original restored, **flag** `company_empty_after_clean` |

---

## 4. Whitespace and invisible characters

| # | Case | Result |
| --- | --- | --- |
| 4.1 | Leading / trailing spaces | Trimmed |
| 4.2 | Repeated internal spaces | Collapsed to one |
| 4.3 | Tab, newline, CR, form feed inside a cell | Converted to a single space |
| 4.4 | Non-breaking space `U+00A0`, narrow `U+202F`, ideographic `U+3000` | Converted to a normal space |
| 4.5 | Zero-width space / ZWNJ / ZWJ / BOM / soft hyphen | Deleted |
| 4.6 | Smart quotes `’ “ ”` | Straightened to `' "` |
| 4.7 | Em dash and en dash | Converted to `-` (they break merge-tag copy) |
| 4.8 | Ellipsis `…` | Converted to `...` |
| 4.9 | Space before punctuation `Acme , Inc` | Tightened |
| 4.10 | Space inside brackets `( Acme )` | Tightened |
| 4.11 | Unicode composition (`é` as e + combining accent) | NFC-normalized so it matches and sorts |
| 4.12 | Whitespace in header names | Trimmed before alias matching |

---

## 5. Phone numbers — not normalized, by design

Earlier drafts of this script split phone numbers into E.164 (country code +
national number). That was removed. A phone column is passed straight through:
no detection, no new column, no reformatting, no reordering of digits.

Reasoning: reformatting a phone number requires knowing its country, and that
is not reliably derivable from the row. Guessing wrong produces a number that
looks plausible but dials the wrong place — worse than leaving it alone. If the
list gets enriched later with verified, geo-tagged numbers, this script must
not have already mangled the original value in a way that's hard to reconcile.

| # | Case | Example | Result |
| --- | --- | --- | --- |
| 5.1 | Any phone value, any format | `(415) 555-1234`, `+91 98765 43210`, `1-800-FLOWERS`, blank | Passed through byte-for-byte, whatever it is |
| 5.2 | Phone starting with `+` on CSV write | `+14155551234` | Written as `+14155551234`, not `'+14155551234`. The CSV formula-injection guard recognizes `+<digit>` as a real number, not a formula, so it is never quote-prefixed |
| 5.3 | Number later enriched/reformatted upstream | any | Also passed through untouched — this script has no opinion on phone formatting at all |

If a normalized phone format is needed later (E.164, split country code, a
dialable link), that is a distinct, separate task — build it deliberately, with
an explicit source of country truth, rather than as a side effect of running
this normalizer.

---

## 6. Locations

| # | Case | Example | Result |
| --- | --- | --- | --- |
| 6.1 | Country aliases | `USA`, `U.S.`, `America` | United States / `US` |
| 6.2 | UK constituents | `England`, `Scotland`, `Wales` | United Kingdom / `GB`, **flag** `uk_constituent_mapped` |
| 6.3 | ISO2 in the country column | `DE`, `SG` | Expanded to full name |
| 6.4 | ISO3 | `USA`, `GBR`, `IND` | Expanded |
| 6.5 | **`CA` ambiguity** | `CA` | California in a State column, Canada in a Country column. Resolved by which column it came from |
| 6.6 | US state code | `TX` | Texas + code `TX` |
| 6.7 | US state name | `texas` | Texas + code `TX` |
| 6.8 | Non-US state | `Maharashtra` | Kept as-is, no code, no flag |
| 6.9 | Three-part free text | `San Francisco, CA, USA` | City / State / Country split |
| 6.10 | Two-part, second is a country | `London, UK` | City + Country |
| 6.11 | Two-part, second is a state | `Austin, TX` | City + State. Country left blank, same no-inference rule as phones |
| 6.12 | Single token that is a country | `Singapore` | Country, and City for city-states |
| 6.13 | Single token that is a state | `Texas` | State + inferred United States |
| 6.14 | Single token, unknown | `Springfield` | City, **flag** if no country resolves |
| 6.15 | LinkedIn area format | `Greater Boston Area`, `Bengaluru Area, India` | `Boston`, `Bengaluru` |
| 6.16 | Renamed cities | `Bangalore`, `Bombay`, `Calcutta`, `Gurgaon`, `Peking`, `Saigon`, `Kiev` | Bengaluru, Mumbai, Kolkata, Gurugram, Beijing, Ho Chi Minh City, Kyiv |
| 6.17 | Abbreviated cities | `NYC`, `SF`, `LA`, `Philly` | Expanded |
| 6.18 | Not a location | `Remote`, `Global`, `EMEA`, `APAC`, `Hybrid` | Cleared out of the geo columns, **flag** `non_geographic_location` |
| 6.19 | Trailing postal code | `Austin, TX 78701` | Stripped |
| 6.20 | More than three parts | `Suite 400, 123 Main, Austin, TX, USA` | Last two win, **flag** `location_extra_parts_dropped` |
| 6.21 | ALL CAPS | `NEW YORK, NY` | New York / New York |
| 6.22 | Diacritics | `São Paulo`, `Zürich`, `Kraków` | Preserved |
| 6.23 | City-states | `Singapore`, `Hong Kong`, `Monaco`, `Luxembourg` | Populate both City and Country, **flag** `city_state_country` |
| 6.24 | Country present but unmapped | | Title-cased, **flag** `country_unmapped` — add it to `COUNTRY_CANON` |
| 6.25 | Ambiguous city across countries | `Perth`, `Cambridge`, `Birmingham`, `London` | Never guessed; the row's country decides |

---

## 7. Deliberately out of scope

These are separate jobs. Doing them inside a normalizer silently changes row
counts, which breaks the one guarantee this script makes.

- Deduplication by email, domain, or fuzzy company match
- Email syntax validation, MX checks, catch-all detection
- Suppression and exclusion lists (use `abm-exclusion-check` for that)
- Enrichment or filling in missing fields
- Domain resolution from a company name
- Title normalization and seniority bucketing
