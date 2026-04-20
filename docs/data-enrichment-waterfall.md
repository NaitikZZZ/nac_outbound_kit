# Data Enrichment Waterfall

> The cheapest-to-expensive flow for turning a raw email list into a fully enriched lead dataset ready for Smartlead and HeyReach.

## The Full Flow

```
Raw leads CSV
     |
     v
[1] Apollo CRM search (FREE)
     |
     v     (70-80% usually found)
     |
     v
[2] Apollo People Match (PAID, 1 credit/lead)
     |
     v     (fills most of remaining 20-30%)
     |
     v
[3] Clay waterfall (PAID, variable)
     |
     v     (work email recovery + phone waterfall)
     |
     v
[4] ZeroBounce (PAID, cheap)
     |
     v     (validates all emails before Smartlead)
     |
     v
Enriched master CSV ready for Smartlead + HeyReach
```

---

## Step 1: Apollo Bulk Lookup (FREE)

**Script:** `scripts/01_apollo_bulk_lookup.py`
**Endpoint:** `POST /contacts/search` (searches existing CRM-synced contacts)
**Cost:** Zero credits (search only, not enrichment)
**Rate limit:** 600 requests/hour

Pulls existing Apollo contacts (synced from your CRM) and returns:
- First name, last name
- Job title
- LinkedIn URL
- Phone numbers (if in CRM)
- Job change events (flags if prospect switched companies)

**Typical hit rate:** 60-80% for US/EU leads, 40-60% for emerging markets.

---

## Step 2: Apollo People Match (PAID)

**Script:** `scripts/02_apollo_enrich_missing.py`
**Endpoint:** `POST /people/bulk_match` (10 per request)
**Cost:** 1 Apollo lead credit per successful match
**Rate limit:** Different quota than contacts/search

Enriches leads NOT found in your existing CRM. Matches against Apollo's full people database.

**Typical hit rate on previously-missing leads:** 5-15% (because many missing leads are generic emails or small companies with no Apollo data).

**When to use:** Always, after Step 1. Cheap compared to the alternative.
**When to skip:** If user has fewer than 50 Apollo credits available.

---

## Step 3: Apollo Direct Dial for Phones (OPTIONAL)

**Script:** `scripts/03_apollo_pull_phones.py`
**Endpoint:** `POST /contacts/search` (pulls existing stored phones, no reveal)
**Cost:** Zero credits (existing CRM phones only)

Apollo stores phone numbers on CRM-synced contacts that aren't returned by `people/bulk_match`. This script pulls them for all contacts found in Step 1.

**Typical hit rate:** 70-85% phone coverage on contacts that had phones in your CRM.

**Important:** True phone enrichment via `reveal_phone_number: true` requires a webhook URL (async callback). For most campaigns, skip phone reveal and rely on Clay waterfall (Step 4) for missing phones.

---

## Step 4: Clay Waterfall (PAID, variable)

**How to run:** Export missing-data leads to CSV, import to Clay, run waterfalls in the Clay UI:

### 4a. Work email waterfall
For leads with invalid / catch-all / generic emails:
1. Find Work Email (LeadMagic)
2. Find Work Email (Findymail)
3. Find Work Email (RocketReach / Wiza / FullEnrich)
4. Validate final result

Expected cost: $0.01-0.05 per validated email

### 4b. Phone waterfall
For leads with no phone number:
1. Find Mobile Phone (LeadMagic - cheapest)
2. Find Mobile Phone (Findymail)
3. Find Phone Number (RocketReach / Datagma)
4. Find Mobile Phone (Prospeo / ContactOut / Wiza)
5. Find Mobile Phone (Enrow / Surfe / FullEnrich)
6. Find phone number (Forager - India-specific if needed)

Expected cost: $0.05-0.30 per found phone, depending on provider coverage

### 4c. Export Clay results back

Clay exports have a final column like `Work Email` or `Mobile Phone` that contains the winning waterfall result. Re-import the CSV into this kit and run `scripts/05_merge_enrichment.py`.

---

## Step 5: ZeroBounce Email Verification (PAID)

**Script:** `scripts/04_zerobounce_verify.py`
**Endpoint:** `GET /v2/validate`
**Cost:** ~$0.008 per email
**Rate limit:** 5 req/sec safe

Classifies every email into:

| Status | Meaning | Action |
|--------|---------|--------|
| `valid` | Confirmed deliverable | Safe to send |
| `catch-all` | Domain accepts all | Send with caution (some bounces) |
| `invalid` | Mailbox doesn't exist | Drop, will bounce |
| `do_not_mail` | Disposable / role / spam trap | Drop |
| `unknown` | Couldn't determine | Drop or re-verify later |
| `error` | Timeout / API error | Retry |

**Critical:** Run this BEFORE uploading to Smartlead. Catch bounces before they touch your sender reputation.

---

## Merge Everything

**Script:** `scripts/05_merge_enrichment.py`

Combines all intermediate CSVs into a single `MASTER_enriched.csv`:
- Original leads
- Apollo bulk lookup results
- Apollo enrich_missing results
- Apollo phones
- Clay work emails
- Clay phones
- ZeroBounce verification results

Adds computed columns:
- `send_to_email` - Clay work email if available, else original email
- `smartlead_ready` - True if ZB status is valid or catch-all
- `heyreach_ready` - True if LinkedIn URL present
- `has_phone` - True if any phone source returned a number

---

## Credit Budget Calculator

For 1,000 leads, rough cost:

| Step | Cost |
|------|------|
| Apollo bulk search | $0 |
| Apollo people match (assuming 30% miss) | ~300 credits = $0-30 depending on plan |
| Apollo phone pull | $0 |
| Clay work email waterfall (assuming 15% miss) | ~$1.50-7.50 |
| Clay phone waterfall (assuming 40% miss) | ~$20-120 |
| ZeroBounce | ~$8 |
| **Total** | **~$30-170 per 1,000 leads** |

Compared to a bare "throw it at Clay for everything" approach (~$200-500), the waterfall saves 50-70%.

---

## Skip Steps For

- **Under 50 leads:** Just run Clay end-to-end, don't waste time splitting
- **Only emails + companies (no LinkedIn needed):** Skip Apollo, go Clay-first
- **Only LinkedIn needed (HeyReach campaigns):** Skip ZeroBounce
- **Already have verified emails:** Skip Steps 1-4, go straight to Smartlead upload
