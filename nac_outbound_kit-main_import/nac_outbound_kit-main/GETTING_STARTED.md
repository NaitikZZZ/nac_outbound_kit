# Getting Started - Your First Campaign

> This guide walks you through running your first campaign end-to-end with this kit. Takes about 30 minutes for a 500-lead campaign.

## What You Need Before Starting

1. **Claude Code installed** (or Claude Desktop with MCP connectors configured)
2. **API keys** for Smartlead, Apollo, ZeroBounce (HeyReach and Clay optional)
3. **A lead list** as a CSV - at minimum with an `email` column
4. **Clarity on the campaign** - which product, which team, which use case, what region

---

## Step-by-Step

### 1. Clone the repo

```bash
git clone <your-org-url>/xoxoday-outbound-kit.git
cd xoxoday-outbound-kit
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up your API keys

```bash
cp .env.example .env
```

Open `.env` in any editor and paste your keys. Never commit this file.

### 4. Open in Claude Code

```bash
claude code .
```

Or open the folder in Claude Desktop. Claude reads `CLAUDE.md` automatically.

### 5. Prepare your lead list

Save your raw leads as `outputs/leads_raw.csv`. At minimum, include an `email` column. Additional helpful columns:
- `company` or `company_name`
- `deal_name` (if from HubSpot passive pipeline)
- `job_title`

Example:

```csv
email,company,deal_name,job_title
john@acme.com,Acme Corp,Acme - Plum API Integration,Product Manager
...
```

### 6. Brief Claude

Type a prompt like:

> I have 500 leads at outputs/leads_raw.csv for a Plum API cold intro campaign, targeting the US market. Team: Global API. Priority P2. My name is Naitik. Campaign launches today. Please enrich, segment, and push to Smartlead.

Claude will:
1. Ask clarifying questions if needed
2. Summarize the plan
3. Run enrichment (Apollo > Clay > ZeroBounce)
4. Segment leads if applicable
5. Generate email copy using templates
6. Create a paused Smartlead campaign with the naming convention
7. Upload leads
8. Export HubSpot-ready CSV
9. Give you a final summary for review

### 7. Review in Smartlead

Open the Smartlead dashboard, find the campaign (will be named per convention, e.g. `P2_API_CUSTOM-US_EMAIL_naitik_16APR26`), verify:
- Sequence preview looks correct
- Sender accounts are region-appropriate
- Schedule matches your target timezone
- Lead count matches what you expected

### 8. Start sending

Flip the campaign from **PAUSED** to **START** in Smartlead when ready.

### 9. Import enriched leads to HubSpot

Import `outputs/HUBSPOT_IMPORT.csv` via HubSpot's import tool. Match `Email` as the unique identifier. Create custom properties for the campaign tracking fields if they don't exist yet.

---

## Typical Campaign Types

### Event campaign (1-day blast)

> I have 266 contacts at outputs/quirks_attendees.csv. Our CRO Abhi is at the Quirks event starting tomorrow. Single email inviting them to meet on-site. US market. P1. My name is Naitik.

### Passive pipeline re-engagement (multi-segment)

> 945 passive deals at outputs/p0_leads.csv for Plum. Segment into Plum API Warm, Cold New Deals, and Empuls/Loyalty. 11-day cadence with email + LinkedIn. Multi-region. P1. My name is Naitik.

### Partner funding trigger

> 40 companies at outputs/recent_funding.csv that raised Series B in the last 30 days. Partnership team pitch. India + US. P2. My name is Priya.

### ABM dream accounts

> 25 dream accounts at outputs/dream_list.csv. ABM team. Multi-stakeholder outreach (3-5 contacts per account). GCC region. P0. My name is Rahul.

---

## Common Questions

### How much will enrichment cost me?

For 1,000 leads:
- Apollo: $0-30 (depending on plan)
- Clay: $20-130 (depending on waterfall depth)
- ZeroBounce: ~$8

Total: **$30-170 per 1,000 leads.** See `docs/data-enrichment-waterfall.md` for the breakdown.

### What if my lead list is messy?

Claude handles messy data. It will flag leads with generic emails (info@, admin@), bounces, and missing fields. You'll get a `bad_data_review.csv` to send back to sales for cleanup.

### Do I need to know Python?

No. Claude runs everything. The scripts are there for Claude (and for reference / manual runs if you want).

### How do I modify the email copy?

Edit files in `templates/email-sequences/`. Claude picks up changes next session. Or just tell Claude "use my custom copy from outputs/my_copy.md" and point to a different file.

### Can I run this for Empuls or Loyalife campaigns?

Yes. The templates default to the Plum angle, but Claude adapts copy to the product. Just specify the product in your brief ("Empuls campaign for HR leaders") and Claude rewrites the value prop accordingly.

### What if Smartlead or HeyReach returns an error?

Claude catches common errors (rate limits, validation errors, 404s) and retries or provides diagnostics. If it's stuck, paste the error back and Claude will troubleshoot.

---

## Support

- Full workflow docs: `CLAUDE.md`
- Naming convention: `docs/campaign-naming-convention.md`
- API details: `docs/smartlead-api-docs.md`, `docs/heyreach-api-docs.md`
- Enrichment flow: `docs/data-enrichment-waterfall.md`
- Cadence details: `docs/cadence-blueprint.md`

Questions? Slack the GTM / Outbound channel.
