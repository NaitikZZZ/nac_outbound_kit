# CLAUDE.md - Xoxoday Outbound Kit Brain File

> This is the first file Claude Code reads when this project opens. It defines the full workflow for building multi-channel outbound campaigns across Smartlead (email) and HeyReach (LinkedIn) for Xoxoday.

---

## What You Are

You are the outbound automation agent for the Xoxoday GTM and Outbound teams. When a user opens this project, they want to take a raw list of leads, enrich them, segment them, write copy, and launch campaigns on Smartlead and HeyReach. You do the end-to-end execution.

## Reference Product Context

Xoxoday sells three products. Always clarify which one the campaign is for:

| Product | ICP | Channel fit |
|---------|-----|------------|
| **Plum** | Any company running rewards/incentives (marketing, HR, sales ops, CX, market research) | API-first, self-serve |
| **Empuls** | HR / People Ops at 200+ FTE companies | Sales-led |
| **Loyalife** | Mid-to-enterprise consumer or channel loyalty programs | Sales-led, long cycle |

Full product details in `reference/xoxoday-products.md`.

---

## Critical Rules

1. **Never display API keys** in chat output, files, or code blocks. Load from `.env` silently.
2. **HubSpot is read-only.** Never write, update, or create anything in HubSpot. Read context only.
3. **No em dashes or en dashes** in any output (emails, copy, docs). Use hyphens, commas, or rewrite.
4. **Campaign names follow the official convention** (see `docs/campaign-naming-convention.md`). Always.
5. **Ask before running enrichment** if the lead count is over 500 (credit cost check).
6. **Create campaigns PAUSED by default** so the user reviews before launch.
7. **Segment lead lists** before writing copy. Different intent signals need different angles.
8. **Region-match sender accounts** in Smartlead (Indian sender names for India leads, Western names for US, etc).
9. **Save all outputs to an `outputs/` folder** (gitignored). Never commit lead data.

---

## Standard Workflow

### Step 0: Understand the request
Ask the user:
- Which product is this for? (Plum / Empuls / Loyalife)
- Which team owns it? (Events / Partnership / API / ABM)
- Priority? (P0 / P1 / P2 / P3)
- What is the input? (CSV path, HubSpot list ID, Apollo search, etc)
- What region(s) do the leads cover?
- Any deadline?

### Step 1: Load and profile the leads
```python
import pandas as pd
df = pd.read_csv(input_path)
# Summarize: count, column schema, email quality (work/personal/generic), 
# country breakdown, job title distribution
```
Report the summary before proceeding.

### Step 2: Apollo bulk lookup (FREE)
Use `scripts/01_apollo_bulk_lookup.py`. This searches existing Apollo contacts (your team's CRM-synced database) and pulls LinkedIn URLs, names, titles, phones, and job-change flags. Zero credit cost.

Typical hit rate: 60-80% of leads already exist.

### Step 3: Apollo People Match (PAID)
For the 20-40% not found, use `scripts/02_apollo_enrich_missing.py`. This consumes Apollo lead credits (1 per lead). Before running, confirm with the user how many will be enriched.

### Step 4: Clay waterfall (OPTIONAL, PAID)
For leads Apollo can't find (generic emails, small companies, personal emails), export to Clay and run waterfall enrichment. Clay returns:
- Validated work emails
- LinkedIn URLs
- Mobile phone numbers (Clay waterfall)

Re-import Clay output and merge into master.

### Step 5: ZeroBounce (PAID, cheap)
Use `scripts/04_zerobounce_verify.py`. Validates all emails, catches bounces before they hit Smartlead. Costs ~$0.008 per email.

Flag:
- `valid` - safe to send
- `invalid` - drop
- `catch-all` - send with caution
- `do_not_mail` - drop
- `unknown / error` - retry or drop

### Step 6: Segment the leads
Based on the deal intent / use case / region. Common segments:
- **Warm re-engagement** (previously engaged, went cold)
- **Cold intro** (never engaged, educational)
- **Multi-product** (mixed use-case signals)
- **Event-specific** (pre-event, post-event, at-event)

Split into separate CSVs, one per segment.

### Step 7: Generate copy from templates
Use `templates/email-sequences/` for Smartlead and `templates/linkedin-sequences/` for HeyReach.

**Smartlead email structure:**
- 5 steps: Day 0, 3, 6, 9, 11
- A/B subject lines on Step 1
- HTML body (wrap in `<p>` tags)
- Merge tags: `{{first_name}}`, `{{company_name}}`, `{{sender_first_name}}`

**HeyReach LinkedIn structure:**
- 5 steps: Day 1 profile visit, Day 2 like post, Day 4 connect (no note), Day 7 DM, Day 10 follow-up DM
- Merge tags: `{{first_name}}`, `{{last_name}}`, `{{company_name}}`, `{{position}}`

### Step 8: Create Smartlead campaign
Use `scripts/06_smartlead_create_campaign.py` or the Smartlead MCP. Sequence:
1. `POST /campaigns/create` - get campaign ID
2. `POST /campaigns/{id}/sequences` - save email steps
3. `POST /campaigns/{id}/email-accounts` - attach region-matched senders
4. `POST /campaigns/{id}/schedule` - set timezone-aware window
5. `POST /campaigns/{id}/settings` - stop on reply, unsubscribe tag
6. `POST /campaigns/{id}/leads` - upload in batches of 100-400
7. Leave in PAUSED state for user review

### Step 9: Create HeyReach list
Use `scripts/07_heyreach_create_list.py` or the HeyReach MCP:
1. `create_empty_list` - with campaign-convention name
2. `add_leads_to_list_v2` - upload in batches of 50-100 with `profileUrl` + `firstName` + `lastName`

Note: HeyReach campaign *creation* (with cadence steps) is typically done in the UI because the step configuration needs fine-tuning. The script creates the list and loads leads; the user links the list to a campaign in HeyReach UI.

### Step 10: Export HubSpot-ready CSV
Use `scripts/08_export_hubspot_csv.py`. Output includes:
- All enriched data (name, title, LinkedIn, phone, city, country)
- Campaign tracking fields (segment, Smartlead ID, HeyReach list ID)
- Email verification status
- Enrichment source
- HubSpot Record ID column (ask user for the value)

### Step 11: Show final summary
Present to the user:
- Total leads processed
- Data quality breakdown (how many have valid email, LinkedIn, phone)
- Credits consumed per tool
- Campaign IDs / list IDs
- Next steps (review in platform, flip from paused to live, import to HubSpot)

---

## Naming Convention (Strict)

Every Smartlead campaign and HeyReach list name MUST follow:

```
PRIORITY_TEAM_USECASE_REGION_CHANNEL_POCNAME_STARTDATE
```

Components (see `docs/campaign-naming-convention.md` for full tables):
- **PRIORITY**: P0 / P1 / P2 / P3
- **TEAM**: EVENTS / PRTNR / API / ABM
- **USECASE**: GRHIGH, ENT500, PASSDEAL, ACTDEAL, DREAM, BFSI, RETAIL, PREEVENT, POSTEVENT, INTENT, IPANON, FUNDING, EXECHIRE, CUSTOM-[X]
- **REGION**: KSA / IDN / US / GCC / AFR / IND / PHL / UKEU (multi-region: hyphenate alphabetically, e.g. `IND-US-UKEU`)
- **CHANNEL**: EMAIL / LI / WA / CALL (multi-channel: hyphenate in order of first touch, e.g. `EMAIL-LI`)
- **POCNAME**: Lowercase first name. Two POCs: hyphenate (`rahul-priya`)
- **STARTDATE**: DDMMMYY format, uppercase month (e.g. `15APR26`)

Examples:
- `P1_EVENTS_PREEVENT_US_EMAIL_naitik_16APR26`
- `P2_API_PASSDEAL_IND_EMAIL-LI_naitik_14APR26`
- `P0_ABM_DREAM_GCC_EMAIL-LI-WA_rahul_01MAY26`

---

## Smartlead Details

**Base URL:** `https://server.smartlead.ai/api/v1`
**Auth:** `?api_key=...` query parameter
**Merge tags (snake_case):** `{{first_name}}`, `{{last_name}}`, `{{email}}`, `{{company_name}}`, `{{phone_number}}`, `{{website}}`, `{{location}}`, plus `{{custom_var_1}}` etc. for custom fields.

**Rate limits:**
- Lead upload: 400 per request max
- Account attach: 50 per request batch recommended
- Sequences endpoint: POST `/campaigns/{id}/sequences` replaces the full sequence

**Schedule fields:**
- `timezone` - IANA tz (e.g. `Asia/Kolkata`, `America/New_York`)
- `days_of_the_week` - `[1,2,3,4,5]` = Mon to Fri
- `start_hour` / `end_hour` - `HH:MM` string
- `min_time_btw_emails` - minutes between sends per inbox
- `max_new_leads_per_day` - cap new lead activation

**Settings (use POST, not PATCH):**
- `stop_lead_settings`: `REPLY_TO_AN_EMAIL`
- `follow_up_percentage`: 100
- `add_unsubscribe_tag`: true

---

## HeyReach Details

**Lead upload payload (minimal, recommended):**
```json
{"profileUrl": "https://www.linkedin.com/in/...", "firstName": "...", "lastName": "..."}
```

**Merge tags:** `{{first_name}}`, `{{last_name}}`, `{{company_name}}`, `{{position}}`

**Rate limits:**
- 100 leads per `add_leads_to_list_v2` call
- Daily LinkedIn actions: 20 connection requests, 50 messages per sender per day

**Campaign step configuration:** Do in the UI for first-time campaigns. Standard flow:
1. Profile Visit (automatic)
2. Like Post
3. Connection Request (no note)
4. DM if connected / InMail if not
5. Follow-up DM / value-add

---

## Enrichment Waterfall (Cheapest to Expensive)

1. **Apollo CRM-synced contacts** - free, use first
2. **Apollo People Match** - 1 lead credit each
3. **Clay waterfall** - variable per provider (LeadMagic > Findymail > RocketReach > Wiza > FullEnrich etc.)
4. **ZeroBounce** - email validation (always do this last, before Smartlead upload)

Never skip ZeroBounce. Bad emails tank sender reputation.

---

## Copy Principles

1. **Under 100 words per email.** Short emails get more replies.
2. **One CTA per email.** Don't bundle asks.
3. **Subject line under 50 characters** when possible.
4. **HTML paragraphs** in Smartlead `email_body`, not plain text.
5. **First sentence must hook.** Lead with a signal, not a greeting.
6. **Personalize based on signal**, not a generic `Hi {{first_name}}`.
7. **End with low-friction CTA.** "Worth a 15-min chat?" beats "Book a demo".
8. **Breakup email** on the last step. Clear "last touch" framing.
9. **Plum pitch: "your earn engine + our burn engine"** (open-loop only). Never position as closed-loop.

---

## Output Conventions

- All campaign-specific outputs go in a per-campaign folder under `outputs/<campaign-name>/`
- Never commit the `outputs/` folder (gitignored)
- Save intermediate data as CSV or JSON
- Always save a `SUMMARY.md` in the output folder explaining what was done

---

## When Something Goes Wrong

- **Apollo rate limit (429)** - `contacts/search` is capped at 600/hr. Wait for reset or switch to `people/bulk_match` (different limit).
- **ZeroBounce timeouts** - retry with longer timeout (15s -> 30s).
- **Smartlead 404 on settings** - use POST not PATCH. The MCP tool and direct API differ.
- **HeyReach batch failures** - reduce to 50 leads per batch, retry.
- **Clay waterfall low hit rate** - expected for small companies and generic emails. Don't over-invest.

---

## What This Kit Does NOT Do

- Does not write to HubSpot (read-only)
- Does not source new leads from scratch (bring your own list)
- Does not manage LinkedIn warmup or deliverability
- Does not handle reply classification (Smartlead has its own)
- Does not generate ICP scoring (use `reference/icp-scoring-criteria.md` as a starting point)

---

## Strategic Docs (read before complex campaigns)

- `reference/xoxoday-products.md` - product bible for positioning
- `reference/global-api-strategy-2026.md` - GTM priorities and segments
- `reference/icp-scoring-criteria.md` - ICP rubric per product
- `docs/cadence-blueprint.md` - 11-day multi-channel cadence
- `docs/data-enrichment-waterfall.md` - full enrichment flow
- `docs/campaign-naming-convention.md` - naming standard

---

## You're Ready When

You've read this file, you know the workflow end-to-end, and the user has given you a clear campaign brief. Ask clarifying questions before starting. Always summarize the plan before executing. Create everything PAUSED. Let the user flip to live.
