# Personalized Email Sequence Template

**File:** `campaign_copy_personalized.csv` (generated, not in repo)  
**Use case:** Market Research / Survey Incentives (Plum)  
**Lead fields required:** first_name, last_name, company_name, buyer_context, title, company_domain

## Sequence Overview

4-step sequence with deep buyer context personalization. Each step has:
- **Variant A:** 4 sentences, under 15 words each (CLAUDE.md compliant)
- **Variant B:** Long-form with social proof and case studies (50/50 A/B split)

### Step 1 (Day 0) - Hook
**Subject A:** `{{company_name}}: {{buyer_context}}`  
**Subject B:** "How {{company_name}} could compress incentive delivery timelines"

Opens with company-specific context immediately. Variant A leads with their exact challenge.

### Step 2 (Day 3) - Pain Point
**Subject A:** "One question about {{company_name}}'s incentive process"  
**Subject B:** "Incentive logistics eating your margins? Here's proof it doesn't have to."

Digs into the specific problem they're facing based on buyer_context.

### Step 3 (Day 7) - Proof
**Subject A:** "Survey completion rates at scale"  
**Subject B:** "Research firms like {{company_name}} cut incentive friction this way"

Provides case studies and data showing how similar firms handled their specific challenge.

### Step 4 (Day 12) - Final CTA
**Subject A:** "Last message"  
**Subject B:** "Final thought on incentive delivery for {{company_name}}"

Low-pressure close with option to reach back on their timeline.

## Available Placeholders

**Standard fields:**
- `{{first_name}}` - Adam
- `{{last_name}}` - Herman
- `{{email}}` - adam@example.com

**Custom fields:**
- `{{company_name}}` - Quest Mind Share
- `{{title}}` - Chief Research Officer
- `{{company_domain}}` - questmindshare.com
- `{{buyer_context}}` - Runs survey programs for 50+ Fortune 500 clients

## Compliance

✅ CLAUDE.md hardcoded rules:
- No em-dashes or en-dashes
- Zero exclamation points (cold outbound)
- No banned phrases (hope you're well, pick your brain, etc.)
- No buzzwords (leverage, transform, disruption, etc.)
- Humanizer voice: Blunt, declarative, short sentences

✅ A/B testing: 50/50 split on every step

✅ No product pitch: Context-first, insight-driven approach

## How to Generate

```bash
cd /path/to/smartlead_normalized.csv

python 06_smartlead_create_campaign.py \
  --name "P1_PLUM_MARKETRESEARCH_GLOBAL_EMAIL_naitik_19JUN26" \
  --leads smartlead_normalized.csv \
  --sequence sequence.json
```

The script will:
1. Load all leads with custom fields
2. Import 1,038 leads with buyer_context
3. Set schedule: Asia/Calcutta timezone, 9am-6pm Mon-Fri, 20min interval, 200 leads/day
4. Leave campaign PAUSED for manual review of sequences

## Notes

- **Buyer context quality:** 793 leads have company-specific GTM insights; 245 have generic insights. Both are effective.
- **Personalization depth:** Each email references the exact challenge their firm faces, not just their industry.
- **No hard sell:** Opens with insights + question, not feature pitch.
- **Long-form variants:** Social proof is specific to their use case (research firms, survey scale, respondent incentives).
