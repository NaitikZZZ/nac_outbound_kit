# Campaign Naming Convention - Xoxoday GTM & Outbound

> Applies to all campaigns in HubSpot, Clay, Smartlead, HeyReach, Interakt, and any other sequencing tool. Use this format every time, across every team (Events, Partnership, API, ABM).

## The Formula

```
PRIORITY _ TEAM _ USECASE _ REGION _ CHANNEL _ POCNAMESTARTDATE _ PROJECTID
```

Separator: underscore `_` between every component. No spaces. No other characters.

The `POCNAMESTARTDATE` component is an exception: **POC name and start date are one token with no separator between them** (e.g. `GauravNaitik25AUG26`), not two underscore-separated pieces. See [POC Name](#poc-name) and [Start Date](#start-date) below. Updated 2026-08-25 to match how the team actually names campaigns; the old `_POCNAME_STARTDATE` two-token form (e.g. `_gaurav-naitik_25AUG26`) is deprecated, don't use it for new campaigns.

The final component, **`PROJECTID`, is the HubSpot Project record ID**, appended after its own underscore (e.g. `..._GauravNaitik11SEP26_98765432`). Added 2026-09-11 as a standing rule across Smartlead, HeyReach, and Interakt so every campaign name traces back to its HubSpot Project record. See [HubSpot Project Record ID](#hubspot-project-record-id) below. Required on every campaign created from this date forward.

Order rationale: **Priority** first for instant triage. **Team and use case** for cross-team grouping. **Region** scopes the audience. **Channel** tells you the motion. **POC name** locks in ownership. **Start date** anchors it. **Project ID** ties it back to HubSpot for tracking.

---

## Components

### Priority

| Code | Label | When to use | Max time to launch |
|------|-------|-------------|--------------------|
| P0 | Critical | CEO / CXO-led push. Highest visibility. | Less than 48 hours |
| P1 | High | Strategic accounts, dream accounts, time-sensitive triggers. | Less than 72 hours |
| P2 | Medium | Standard ICP campaigns, industry-specific, event-driven. | Within 1 week |
| P3 | Low | Nurture, awareness, experimental. | Within 2 weeks |

### Team

| Shorthand | Team |
|-----------|------|
| EVENTS | Events |
| PRTNR | Partnership |
| API | Global API |
| ABM | Account-Based Marketing |

### Use Case

| Code | Description |
|------|-------------|
| GRHIGH | Growth rate over 20% (headcount or revenue signal) |
| ENT500 | Employee size over 500 |
| PASSDEAL | Passive deal (not actively evaluating, nurture) |
| ACTDEAL | Active deal (in-pipeline, evaluation stage) |
| CAMACC | Campaign account (already in active sequence) |
| DREAM | Dream account (top-priority named account) |
| BFSI | Industry: Banking, Financial Services, Insurance |
| RETAIL | Industry: Retail, E-Commerce |
| PREEVENT | Pre-event outreach (awareness, invite, registration) |
| POSTEVENT | Post-event follow-up (attendees, no-shows) |
| INTENT | Intent signal triggered (Bombora / G2 spike) |
| IPANON | IP de-anonymized visitor (Clearbit / 6sense / Albacross) |
| FUNDING | Funding trigger (recent round closed) |
| EXECHIRE | Executive hire trigger (new CXO / VP joined) |
| CUSTOM-[X] | Anything not in this list. Replace [X] with a short descriptor (e.g. `CUSTOM-CHRO`) |

**Tip:** For industry campaigns, always use the industry code (BFSI, RETAIL, etc.) rather than CUSTOM. Create new 4-6 letter codes in the team wiki for recurring industries.

### Region

| Code | Region |
|------|--------|
| KSA | Kingdom of Saudi Arabia |
| IDN | Indonesia |
| US | United States |
| GCC | Gulf Cooperation Council (UAE, Qatar, Bahrain, Kuwait, Oman) |
| AFR | Africa |
| IND | India |
| PHL | Philippines |
| UKEU | UK and Europe |
| GLOBAL | Worldwide / no single region, targeting spans all of the above |

**Multi-region rule:** Combine codes with hyphens, alphabetically sorted.
- `KSA-IDN-GCC`
- `IND-US-UKEU`

`GLOBAL` is a standalone code, don't combine it with other region codes.

### Channel

| Code | Channel |
|------|---------|
| EMAIL | Email outreach (Smartlead, HubSpot sequences) |
| LI | LinkedIn outreach (HeyReach) |
| WA | WhatsApp (Interakt) |
| CALL | Cold / warm calling |

**Multi-channel:** List channels in order of first touch, hyphenated.
- `EMAIL-LI` = email fires first, LinkedIn follows
- `EMAIL-WA-CALL` = all three in that order

### POC Name

Updated 2026-09-11: the POC name token is now **Requestor + Campaign Owner**, not just the campaign owner alone.

- **Requestor** - who asked for this campaign, pulled from the `requestor` property on the linked HubSpot Project record.
- **Campaign Owner** - who is actually building/pushing the campaign, pulled from the Project's `hubspot_owner_id` (the Project's assigned owner).

TitleCase first name only for each, no spaces, no separators, concatenated directly with Requestor first and Campaign Owner second. If a campaign has no separate requestor (owner requested their own work), the name is just the owner's first name, same as before.

| Requestor | Campaign Owner | Write as |
|-----------|-----------------|---------|
| (none / self-requested) | Rahul Sharma | `Rahul` |
| Gaurav Agarwal | Naitik Chavda | `GauravNaitik` |
| Priya Nair | Naitik Chavda | `PriyaNaitik` |

This replaces the old "co-owners concatenated" reading of multi-name tokens (e.g. `GauravNaitik` used to mean "Gaurav + Naitik co-own"; it now means "Gaurav requested, Naitik owns/pushed the campaign"). Genuine multi-owner campaigns (no distinct requestor) still concatenate co-owner first names in the order given, as before.

### Start Date

`DDMMMYY` with uppercase three-letter month, appended **directly to the POC name with no separator**. Always the date the campaign is actually created/pushed to the platform (today's date at build time) - never a planned future go-live date, even if the campaign will stay paused for a while before launch.

| Date | Format |
|------|--------|
| January 1, 2026 | `01JAN26` |
| April 15, 2026 | `15APR26` |
| November 30, 2026 | `30NOV26` |

Combined with POC name: `Naitik25AUG26`, `GauravNaitik25AUG26`.

### HubSpot Project Record ID

Added 2026-09-11. Every campaign in this kit is tied to a Project record in HubSpot (portal 6512810, `PROJECT` object). The final token in the name is that Project's numeric record ID, appended after an underscore: `..._<POCNAMESTARTDATE>_<PROJECTID>` (e.g. `..._GauravNaitik11SEP26_98765432`).

Purpose: lets anyone trace a Smartlead campaign, HeyReach list/campaign, or Interakt push straight back to the HubSpot Project it belongs to, without cross-referencing a spreadsheet.

Sourcing: fully automatic via `scripts/hubspot_project_lookup.py` (direct HubSpot REST API, read-only - not the HubSpot MCP connector, whose OAuth grant is missing Project-object access as of 2026-09-11; the private app token used here is a separate credential and isn't affected by that). Run `python3 scripts/hubspot_project_lookup.py --search "<project name or keyword>"` (or `--id <record_id>` if already known) - it returns `record_id`, `requestor_name`, and `campaign_owner_name` directly, already resolved from the raw owner IDs (needs the `crm.objects.owners.read` scope on the private app, added 2026-09-11). Build the POC token from `requestor_name` + `campaign_owner_name` + today's date, and append `_<record_id>` as the final suffix.

If the script errors (token revoked, no matching Project, etc.), ask the user for the Project record ID and requestor/owner names directly instead of skipping the suffix - it is not optional.

---

## Full Examples

Pre-2026-09-11 examples (no Project ID suffix, POC token is owner-only or co-owner-only):

| Campaign Name | What It Means |
|---------------|---------------|
| `P0_ABM_DREAM_US_EMAIL_Rahul01JAN26` | ABM, Dream account, US, Email, Rahul, Critical, Jan 1 2026 |
| `P1_EVENTS_PREEVENT_IND_EMAIL-LI_Priya15APR26` | Events, Pre-event, India, Email + LinkedIn, Priya, High, Apr 15 2026 |
| `P2_ABM_BFSI_GCC_LI_Arjun01MAY26` | ABM, BFSI industry, GCC, LinkedIn, Arjun, Medium, May 1 2026 |
| `P1_ABM_INTENT_KSA-IDN-GCC_EMAIL-WA_Rahul10FEB26` | ABM, Intent signal, ROW, Email + WhatsApp, Rahul, High, Feb 10 2026 |
| `P2_PRTNR_FUNDING_US_EMAIL_Neha20MAR26` | Partnership, Funding trigger, US, Email, Neha, Medium, Mar 20 2026 |
| `P3_API_ENT500_UKEU_EMAIL-LI_Sam01JUN26` | API, Employee 500+, UK/EU, Email + LinkedIn, Sam, Low, Jun 1 2026 |
| `P1_ABM_POSTEVENT_IND_WA-CALL_Priya20APR26` | ABM, Post-event, India, WhatsApp + Call, Priya, High, Apr 20 2026 |
| `P2_ABM_POSTEVENT_IND_WA_Priya05MAR26` | ABM, Post-event, India, WhatsApp only (Interakt), Priya, Medium, Mar 5 2026 |
| `P0_EVENTS_DREAM_US_EMAIL-LI_RahulPriya05JAN26` | Events, Dream accounts, US, Email + LinkedIn, Rahul + Priya (co-own), Critical, Jan 5 2026 |
| `P0_ABM_API-HealthandWellness_GLOBAL_EMAIL-LI_GauravNaitik25AUG26` | ABM, custom use case, Global, Email + LinkedIn, Gaurav + Naitik (co-own), Critical, Aug 25 2026 |

Current format (from 2026-09-11 on), with the HubSpot Project ID suffix and Requestor+Owner POC token:

| Campaign Name | What It Means |
|---------------|---------------|
| `P0_ABM_DREAM_US_EMAIL_Naitik11SEP26_98765432` | ABM, Dream account, US, Email, Naitik (self-requested), Critical, Sep 11 2026, HubSpot Project 98765432 |
| `P1_EVENTS_PREEVENT_IND_EMAIL-LI_GauravNaitik11SEP26_45612378` | Events, Pre-event, India, Email + LinkedIn, requested by Gaurav / owned by Naitik, High, Sep 11 2026, HubSpot Project 45612378 |
| `P2_ABM_BFSI_GCC_LI_PriyaNaitik11SEP26_11223344` | ABM, BFSI industry, GCC, LinkedIn, requested by Priya / owned by Naitik, Medium, Sep 11 2026, HubSpot Project 11223344 |

---

## 7 Steps to Name Your Campaign

1. **Set priority** - Board-level (P0), strategic (P1), standard (P2), nurture (P3)
2. **Identify team** - EVENTS / PRTNR / API / ABM
3. **Pick use case** - see Section 3.3. If not listed, use `CUSTOM-[X]`
4. **Define region** - use region code, multi-region hyphenated alphabetically, or `GLOBAL` for worldwide
5. **Choose channel(s)** - single or hyphenated in first-touch order
6. **Add POC name + start date as one token** - TitleCase requestor first name (if any) + campaign owner first name, concatenated with no separator, then today's date as `DDMMMYY` appended directly with no separator (e.g. `GauravNaitik11SEP26`)
7. **Append the HubSpot Project record ID** - underscore, then the Project's numeric record ID (e.g. `_98765432`)

---

## Common Mistakes

- Writing `P1-EVENTS-...` with hyphens instead of underscores (underscores between components, hyphens only within multi-region / multi-channel)
- Forgetting the start date
- Using full names (`rahul-sharma`) instead of just first name (`Rahul`)
- Lowercase POC name (`rahul` instead of `Rahul`)
- Hyphenating co-owned POC names (`gaurav-naitik` instead of `GauravNaitik`) - that format is deprecated
- Putting an underscore between POC name and start date (`Rahul_01JAN26` instead of `Rahul01JAN26`)
- Lowercase month (`apr26` instead of `APR26`)
- Using "Email" or "LinkedIn" as free text instead of the codes (`EMAIL`, `LI`)
- Using region names like "India" instead of codes (`IND`)
- Forgetting the HubSpot Project record ID suffix, or putting it before the POC name/date instead of after
- Using a planned future launch date instead of today's date (the build/push date) for the Start Date component

---

*Xoxoday | GTM and Outbound Team | Internal Use Only*
