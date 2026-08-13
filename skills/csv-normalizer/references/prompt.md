# Standalone normalization prompt

For a small pasted list, a Clay AI column, or any environment without Python.
Over roughly 200 rows, use `scripts/normalize.py` instead: an LLM will silently
drop or merge rows on long inputs, and this task has to preserve row count exactly.

---

## Full-table prompt

> You are a data normalizer for a cold email campaign. Clean the table below.
>
> **Hard rules**
> 1. Output exactly as many rows as the input. Never drop, merge, reorder, or dedupe.
> 2. Never overwrite an input column. Add new columns named `Cleaned <X>`.
> 3. Never invent a value. Blank stays blank.
> 4. When a value is ambiguous, leave the cleaned cell blank and write the reason in `Flags`.
> 5. Preserve diacritics and non-Latin scripts exactly. Never transliterate to ASCII.
>
> **Add these columns:** `Cleaned Full Name`, `Cleaned First Name`, `Cleaned Last Name`, `Cleaned Company`, `Cleaned City`, `Cleaned State`, `Cleaned Country`, `Country Code`, `Flags`. Do not add a phone column — see the Phones rule below.
>
> **Names**
> - Keep the original full name. Also split it: First Name is the first token, Last Name is every remaining token, so middle names, initials, and particles like `van der` stay with the surname.
> - Remove honorifics (`Mr`, `Dr`, `Prof`, `Shri`, `Adv`), credential and generational suffixes (`Jr`, `III`, `PhD`, `MBA`, `CPA`, `PMP`), pronouns (`(she/her)`), emoji, and LinkedIn banner text (`| Open to Work`, `— We're Hiring`).
> - `Smith, John` becomes `John Smith`. But `Smith, John, MBA` keeps the order and just drops `MBA`.
> - Fix casing only when the input is entirely uppercase or entirely lowercase. Leave `McKinsey`, `DeAndre`, and `iPhone` alone.
> - `mcdonald` becomes `McDonald`. Do not touch `Mac` names. `o'brien` becomes `O'Brien`. Particles stay lowercase: `van der Berg`.
> - Single-token names go in First Name with Last Name blank. Flag `mononym`.
> - `Hi`, `There`, `Team`, `Info`, `Sales` are not names. Flag `placeholder_first_name`.
>
> **Companies**
> - Strip trailing legal suffixes: `Inc`, `Inc.`, `Corp`, `Ltd`, `Limited`, `LLC`, `LLP`, `PLC`, `Co`, `Company`, `GmbH`, `AG`, `BV`, `NV`, `AB`, `S.A.`, `SAS`, `SRL`, `Pvt Ltd`, `Pte Ltd`, `Pty Ltd`, `Sdn Bhd`, `K.K.`, `Sp. z o.o.`, `Ltda`, `FZCO`. Repeat until none remain: `Acme Holdings Pvt. Ltd. Co.` becomes `Acme Holdings`.
> - Strip descriptor tails: `Cora, a company of Blank` becomes `Cora`. `Audible, an Amazon Company` becomes `Audible`. Also handle `, part of X`, `, a division of X`, `(formerly X)`, `dba X`.
> - If stripping would empty the name or leave only an article, keep the original. `The Limited` stays `The Limited`.
> - Only strip a suffix at the end. `Limited Brands` and `Corporate Express` keep their first word.
> - `Unlimited Company` drops only `Company`: `LinkedIn Ireland Unlimited Company` becomes `LinkedIn Ireland Unlimited`.
> - Remove bracketed quality markers (`(DUPE)`, `[TEST]`) and trailing `- DO NOT USE`. Never remove those words mid-name: `Old Dominion University` and `Avalon Test Equipment` are unchanged.
> - Fix casing only for entirely-uppercase or entirely-lowercase input. Inside an ALL CAPS name, keep short non-word tokens uppercase as acronyms: `FMFE, CPA, P.C.` becomes `FMFE, CPA`, but `OLD WORLD INDUSTRIES` becomes `Old World Industries`.
> - Preserve known brand casing: `LinkedIn`, `eBay`, `HubSpot`, `PayPal`, `OpenAI`, `McKinsey`, `IBM`, `KPMG`, `PwC`, `AT&T`.
> - Convert `and` to `&` only between two capitalized words. `Marcus and Millichap` becomes `Marcus & Millichap`.
> - Keep a leading `The`, a `| tagline`, and geographic parentheticals unless told otherwise.
> - If the cell is a bare domain like `acme-widgets.com`, derive `Acme Widgets` and flag `derived_from_domain`.
>
> **Whitespace**
> - Trim ends, collapse repeated spaces, convert tabs and newlines to a space, delete zero-width and non-breaking characters, straighten smart quotes, convert em and en dashes to a hyphen, remove space before punctuation.
>
> **Phones**
> - Leave any phone number column completely untouched. Copy the value through exactly as it appears in the input: same formatting, same punctuation, same everything. Do not reformat it, split it, add a country code, or add any new phone-related column. This applies even if the number looks messy or inconsistent with other rows — do not "fix" it.
>
> **Locations**
> - Standardize countries to a full name plus ISO2: `USA`/`U.S.`/`America` to `United States`/`US`; `England`/`Scotland`/`Wales`/`UK` to `United Kingdom`/`GB`.
> - `CA` means California in a state column and Canada in a country column.
> - Expand US state codes both ways. Leave non-US states as plain names.
> - `Greater Boston Area` becomes `Boston`. `Bengaluru Area, India` becomes `Bengaluru` + `India`.
> - Update renamed cities: Bangalore to Bengaluru, Bombay to Mumbai, Calcutta to Kolkata, Gurgaon to Gurugram, Kiev to Kyiv, Saigon to Ho Chi Minh City.
> - `Remote`, `Global`, `EMEA`, `APAC`, `Hybrid` are not places. Clear the geo columns and flag it.
> - Never guess the country for an ambiguous city (`Perth`, `Cambridge`, `Birmingham`, `London`). Leave it and flag.
>
> Return the full table as CSV. After the table, list every flagged row with its row number and the reason.
>
> ```
> <paste table here>
> ```

---

## Single-cell variants

**Company only** (good as a Clay AI column):

> Return only the cleaned company name, nothing else. Strip trailing legal suffixes (Inc, Ltd, LLC, Corp, Company, GmbH, Pvt Ltd, Pte Ltd, S.A., and equivalents), repeating until none remain. Strip descriptor tails like ", a company of X", ", an X Company", ", part of X", "(formerly X)". If stripping would leave nothing or only an article, return the original unchanged. Only strip suffixes at the end, never mid-name. Fix casing only if the input is entirely uppercase or entirely lowercase, keeping short non-word tokens uppercase as acronyms and preserving known brand casing like LinkedIn, eBay, HubSpot, IBM, PwC. Convert "and" to "&" between capitalized words. Keep a leading "The". Preserve diacritics. If the input is a domain, return the brand name derived from it.
>
> Input: {{company}}

**First name only:**

> Return only the person's first name, nothing else. Strip honorifics, credentials, suffixes, pronouns, emoji, and LinkedIn banner text. If the input is "Last, First", return First. Fix casing only if the input is entirely uppercase or entirely lowercase. Keep diacritics. If the input is a placeholder like "Hi", "There", "Team", or "Info", return an empty string.
>
> Input: {{full_name}}
