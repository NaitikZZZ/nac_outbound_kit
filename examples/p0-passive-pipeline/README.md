# Example: P0 Passive Pipeline Re-engagement (945 leads)

> Worked example from April 2026. 945 cold HubSpot passive deals re-engaged across 3 segments on both Smartlead and HeyReach.

## The Brief

- **Input:** 945 leads from HubSpot passive pipeline, each with email + company + deal name + (sometimes) job title
- **Product:** Plum (Global API)
- **Team:** Global API
- **Priority:** P1
- **Regions:** Multi (India 40%, US 12%, Europe 13%, APAC 6%, META 5%, unknown 20%)
- **Outcome:** 3 Smartlead campaigns + 3 HeyReach lists, all paused for review

## Pipeline Steps

### 1. Enrichment (3 hours)

| Stage | Tool | Result |
|-------|------|--------|
| Apollo bulk search | Free | 611/945 found (65%) |
| Apollo people match | ~10 credits | +9 added (620 total) |
| Clay work email waterfall | ~$1.50 | +108 new work emails (for invalid ZB status leads) |
| Apollo phones (from CRM) | Free | 498 phones |
| Clay phone waterfall | ~$60 | +128 new phones (626 total) |
| ZeroBounce verification | ~$7.50 | 519 valid, 258 invalid (caught!), 62 catch-all |

**Final data quality:**
- 688 Smartlead-ready (73%)
- 621 HeyReach-ready (66%)
- 626 have phone (66%)
- 546 fully loaded (all 3 channels)

### 2. Segmentation (30 min)

Split by deal name intent:

| Segment | Count | Angle |
|---------|-------|-------|
| C1 - Plum API Warm | 372 | Re-engagement (deal names contained Plum / API / Integration / SSO) |
| C2 - Passive New Deals | 480 | Cold intro (generic "New Deal" entries) |
| C3 - Empuls / Loyalty / Other | 93 | Multi-product platform pitch |

### 3. Copy generation (via templates)

Used `templates/email-sequences/re-engagement-5step.md` for C1, `cold-intro-5step.md` for C2, `multi-product-5step.md` for C3. Each with 5 email steps, A/B subject on Step 1.

Used corresponding `templates/linkedin-sequences/` files for HeyReach.

### 4. Smartlead setup (1 hour)

3 campaigns created with region-matched sender accounts:

| Campaign | ID | Leads Uploaded | Blocked |
|----------|-----|----------------|---------|
| P1_API_PASSDEAL_[regions]_EMAIL-LI_naitik_14APR26 (C1) | 3178227 | 290 | 45 |
| ... (C2) | 3178228 | 319 | 55 |
| ... (C3) | 3178229 | 79 | 10 |

All 272 sender accounts attached (100 Indian + 60 EU + 80 META + 30 SEA). Timezone set to `Asia/Kolkata` as primary (Smartlead handles per-lead).

### 5. HeyReach setup

3 lists created, Gaurav Sava's LinkedIn account (ID: 168813) as sender.

| List | ID | Leads Added |
|------|-----|-------------|
| P0-C1-Plum-API-Warm-Apr2026 | 614694 | 254 |
| P0-C2-Passive-New-Deals-Apr2026 | 614695 | 293 |
| P0-C3-Empuls-Loyalty-Other-Apr2026 | 614696 | 70 |

Campaigns themselves configured in HeyReach UI (5-step cadence: visit, like, connect, DM, follow-up DM).

### 6. HubSpot import

Exported `HUBSPOT_IMPORT_945_leads.csv` with:
- 945 rows, 27 columns
- Record ID 759186512592 as primary key
- Campaign tracking fields (segment, Smartlead ID, HeyReach ID)
- Data quality flags

### 7. Data quality feedback to sales team

Flagged 257 leads with bad data (bounced emails, no LinkedIn, generic info@ addresses) and sent a structured email to sales + RevOps team asking for contact clean-up.

## Total Time Invested

- Enrichment: 3 hours (mostly waiting on APIs)
- Segmentation + copy: 1 hour
- Platform setup: 2 hours
- **Total: 6 hours for 945 leads across 3 campaigns**

Without this kit, expected time: 2-3 days across 2-3 people.

## Total Cost

- Apollo: $10 (10 lead credits)
- Clay: $60 (phone waterfall + work email)
- ZeroBounce: $7.50
- **Total: ~$77.50 for 945 enriched leads**

## Files Generated (not in repo, stays in outputs/)

- `MASTER_945_enriched_v4.csv` - complete master with all enrichment
- `campaign1/2/3_FINAL_*_smartlead.csv` - per-segment Smartlead uploads
- `campaign1/2/3_FINAL_*_heyreach.csv` - per-segment HeyReach uploads
- `HUBSPOT_IMPORT_945_leads.csv` - HubSpot-ready import
- `bad_data_257_for_team_review.csv` - data quality issues
- `HeyReach_LinkedIn_Copy_All_3_Campaigns.docx` - printable copy doc
- `P0_Passive_Pipeline_Campaign_Plan.pdf` - printable campaign plan
