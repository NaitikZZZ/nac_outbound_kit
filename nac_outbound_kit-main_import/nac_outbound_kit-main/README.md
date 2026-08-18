# Xoxoday Outbound Kit

> End-to-end Claude Code toolkit for enriching, segmenting, and launching multi-channel outbound campaigns across **Smartlead (email)** and **HeyReach (LinkedIn)**. Built for the Xoxoday GTM and Outbound teams.

Turn a raw list of companies or HubSpot passive deals into a live multi-channel campaign in a few hours, with Claude Code doing the enrichment, segmentation, copywriting, and platform setup.

---

## What This Kit Does

Given a raw lead list (emails, company names, deal names), Claude Code will:

1. Enrich contacts via **Apollo** (LinkedIn URL, name, title, phone) using existing CRM data first to save credits
2. Fill gaps via **Clay waterfall** (work email recovery, phone waterfall)
3. Verify every email with **ZeroBounce**
4. Segment leads into campaign buckets (warm, cold, multi-product, etc)
5. Generate 5-step email sequences and 5-step LinkedIn sequences per segment
6. Create campaigns in **Smartlead** with region-matched sender inboxes and timezone-aware schedules
7. Create lists in **HeyReach** and load prospects
8. Export HubSpot-ready CSVs with campaign tags, data-quality flags, and record IDs

Everything runs via natural-language prompts to Claude Code - no manual API calls, no copy-paste between tools.

---

## Repo Structure

```
xoxoday-outbound-kit/
├── README.md                       You are here
├── CLAUDE.md                       Brain file. Claude Code reads this first.
├── GETTING_STARTED.md              Step-by-step for first-time users
├── .env.example                    Copy to .env, fill in API keys
├── .gitignore                      Keep .env and outputs out of git
├── requirements.txt                Python dependencies
│
├── docs/                           Reference docs
│   ├── campaign-naming-convention.md   Official naming standard
│   ├── smartlead-api-docs.md           Smartlead endpoints
│   ├── heyreach-api-docs.md            HeyReach endpoints
│   ├── data-enrichment-waterfall.md    Apollo > Clay > ZeroBounce flow
│   └── cadence-blueprint.md            11-day multi-channel cadence
│
├── templates/                      Copy-paste sequence templates
│   ├── email-sequences/
│   │   ├── re-engagement-5step.md       Passive/warm leads
│   │   ├── cold-intro-5step.md          Cold leads, educational
│   │   ├── multi-product-5step.md       Mixed use-case
│   │   └── event-1step.md               Event outreach, single shot
│   └── linkedin-sequences/
│       ├── re-engagement-5step.md       HeyReach copy for warm re-engagement
│       ├── cold-intro-5step.md          HeyReach cold intro
│       └── multi-product-5step.md       HeyReach multi-product
│
├── scripts/                        Reusable Python scripts
│   ├── 01_apollo_bulk_lookup.py         Pull existing Apollo contacts
│   ├── 02_apollo_enrich_missing.py      Enrich missing leads via People Match
│   ├── 03_apollo_pull_phones.py         Pull phones from CRM-synced contacts
│   ├── 04_zerobounce_verify.py          Validate all emails
│   ├── 05_merge_enrichment.py           Merge Apollo + Clay + ZeroBounce
│   ├── 06_smartlead_create_campaign.py  Create Smartlead campaign end-to-end
│   ├── 07_heyreach_create_list.py       Create HeyReach list and upload leads
│   └── 08_export_hubspot_csv.py         HubSpot-ready import file
│
├── reference/                      Internal Xoxoday context
│   ├── xoxoday-products.md              Plum, Empuls, Loyalife bible
│   ├── global-api-strategy-2026.md      2026 GTM strategy
│   └── icp-scoring-criteria.md          ICP rubric
│
└── examples/                       Worked examples
    └── p0-passive-pipeline/             945-lead P0 campaign walkthrough
```

---

## Quickstart (5 Minutes)

### 1. Clone / download
```bash
git clone <repo-url> xoxoday-outbound-kit
cd xoxoday-outbound-kit
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up API keys
```bash
cp .env.example .env
# Open .env and fill in your personal API keys (see below)
```

You need keys for:
- **Smartlead** - Settings > API Keys
- **Apollo** - Settings > Integrations > API
- **ZeroBounce** - My Account > API
- **HeyReach** - MCP connector handles auth (no key needed if MCP is installed)
- **Clay** - Workspace Settings > API

### 4. Open in Claude Code
Open this folder in Claude Code (or Claude Desktop with MCP servers configured). Claude reads `CLAUDE.md` first and knows the full workflow.

### 5. Start with a natural-language prompt
```
I have a raw lead list at /path/to/leads.csv with columns email, company, deal_name.
Build me 3 segmented campaigns for the Xoxoday Plum API angle.
```

Claude handles the rest.

---

## Who Should Use This Kit

| Team | Use Case |
|------|---------|
| **Events** | Pre-event + post-event outreach, meet-at-booth campaigns |
| **Partnership** | Partner trigger campaigns, funding event outreach |
| **Global API** | Plum / Loyalife outbound for rewards infrastructure |
| **ABM** | Dream account, intent signal, IP de-anon campaigns |

---

## Campaign Naming Convention

All campaigns follow this structure:

```
PRIORITY_TEAM_USECASE_REGION_CHANNEL_POCNAME_STARTDATE
```

Example: `P1_EVENTS_PREEVENT_US_EMAIL_naitik_16APR26`

See [docs/campaign-naming-convention.md](docs/campaign-naming-convention.md) for the full standard.

---

## Required Tools / MCP Connectors

Claude Code needs access to these MCP servers (set up once per machine):

| Tool | Purpose | Setup |
|------|---------|-------|
| **Smartlead MCP** | Email campaign creation, lead upload, analytics | `claude_desktop_config.json` |
| **HeyReach MCP** | LinkedIn list + campaign management | Via Claude connector |
| **Apollo MCP** | Lead enrichment, people search | Via Claude connector |
| **Clay MCP** | Waterfall enrichment (email, phone, LinkedIn) | Via Claude connector |
| **HubSpot MCP** (read-only) | Pull existing CRM context | Via Claude connector |

If any of these are missing, ask your IT/RevOps team to provision them.

---

## Data Flow at a Glance

```
Raw leads CSV
   |
   v
[1] Apollo bulk lookup (existing CRM contacts)        ~0 credits
   |
   v
[2] Apollo People Match (leads NOT in CRM)            ~1 credit / lead
   |
   v
[3] Clay waterfall (cheapest to expensive)            ~$0.01-0.05 / lead
   |
   v
[4] ZeroBounce verify                                 ~$0.008 / email
   |
   v
[5] Segment by deal intent / region / use case
   |
   v
[6] Generate email + LinkedIn copy per segment
   |
   v
[7] Push to Smartlead (email) + HeyReach (LinkedIn)
   |
   v
[8] Export HubSpot-ready CSV with campaign tags
```

Every step is scripted. You can run the full pipeline end-to-end, or pause/inspect at any stage.

---

## Security Rules (Read Before Using)

1. **Never commit `.env`** - it contains API keys. Already in `.gitignore`.
2. **HubSpot is read-only.** This kit never writes to HubSpot. All enrichment goes to Smartlead, HeyReach, and local CSVs.
3. **Never paste API keys in chat** with Claude - store them in `.env` and Claude reads them from there.
4. **Outputs folder is gitignored** - lead data stays local, never in the repo.

---

## Support

- Questions about this kit: ping the Xoxoday GTM / Outbound Slack channel
- Campaign naming questions: see [docs/campaign-naming-convention.md](docs/campaign-naming-convention.md)
- API issues: check the tool-specific docs in `docs/`
- Stuck on a step: open Claude Code and ask - it knows the full workflow

---

## Credits

Built by Naitik Chavda (naitik.chavda@xoxoday.com). Licensed for internal Xoxoday use only.
