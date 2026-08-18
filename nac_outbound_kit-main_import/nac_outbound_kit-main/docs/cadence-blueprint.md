# 11-Day Multi-Channel Cadence Blueprint

> Applied to all standard outbound campaigns. Adapt messaging per segment, but keep the cadence structure consistent.

## Overview

| Day | Channel | Action | Owner | Automation |
|-----|---------|--------|-------|-----------|
| D1 | Email | Email 1 - Cold open | ABM | Smartlead Step 1 |
| D1 | LinkedIn | Profile visit | ABM | HeyReach Step 1 |
| D2 | LinkedIn | Like / comment on prospect's post | ABM | HeyReach Step 2 |
| D3 | Email | Email 2 - Use-case proof point | ABM | Smartlead Step 2 |
| D4 | LinkedIn | Connection request (NO note) | ABM | HeyReach Step 3 |
| D5 | Phone | SDR Call 1 | SDR | Manual |
| D6 | Email | Email 3 - Competitive differentiation | ABM | Smartlead Step 3 |
| D7 | LinkedIn | DM (if connected) / InMail (if not) | ABM | HeyReach Step 4 |
| D8 | Phone | SDR Call 2 + voicemail | SDR | Manual |
| D9 | Email | Email 4 - Direct CTA / sandbox offer | ABM | Smartlead Step 4 |
| D10 | LinkedIn | DM 2 - Breakup / value add | ABM | HeyReach Step 5 |
| D11 | All | Final multi-channel breakup | ABM / SDR | Smartlead Step 5 |

## Metrics to Track

| Metric | Target |
|--------|--------|
| Email reply rate | > 3% |
| LinkedIn connection acceptance | > 15% |
| LinkedIn DM reply rate | > 8% |
| Call connect rate | > 8% |
| Meeting book rate (from total contacted) | > 3% |

## Channel Split

### Smartlead handles
- All 5 email touches (D1, D3, D6, D9, D11)
- A/B testing on Step 1 subject lines
- Stop on reply (auto-pauses follow-ups)
- Timezone-aware scheduling per lead

### HeyReach handles
- Profile visit (D1)
- Post like (D2)
- Connection request (D4)
- DM / InMail (D7)
- Follow-up DM (D10)

### SDR team handles manually
- Call 1 (D5) - first live voice touch, references email + LinkedIn activity
- Call 2 (D8) - second dial, voicemail if no pickup

## Coordination Rules

1. **Day 1 sync:** Email Step 1 and LinkedIn profile visit should fire on the same business day. Don't let LinkedIn run ahead - prospects notice the "someone viewed your profile" notification before the email lands.
2. **Reply anywhere = stop everywhere:** If a prospect replies on email, pause LinkedIn and cancel calls. Smartlead does email auto-pause; HeyReach needs manual pause on reply (set up via webhooks or daily list scrub).
3. **Connection accepted = skip InMail:** HeyReach defaults to DM-if-connected logic on Step 4. Leave it on.
4. **Holiday / weekend skip:** Set `days_of_the_week: [1,2,3,4,5]` in Smartlead schedule. HeyReach should mirror in campaign settings.
5. **Timezone matching:** Each lead's timezone drives their send window. India leads get IST schedule, US leads get EST, etc. Smartlead handles this when sender accounts have region-matched names and proper timezone config.

## Variations

### Event campaigns (shorter cadence)
- D1: Single email invite to meet at venue
- D2-3: LinkedIn DM or InMail follow-up if no reply
- Stop after event ends

### Active / hot deal (faster cadence)
- Compress to 7 days instead of 11
- Day gaps: 0, 1, 3, 5, 7

### Nurture / low priority (slower cadence)
- Stretch to 30 days
- Day gaps: 0, 5, 10, 15, 25, 30

## Content Principles per Step

| Step | Purpose |
|------|---------|
| Email 1 | Value hook. Segment-specific pain point. Short. |
| Email 2 | Social proof / case study relevant to their segment. |
| Email 3 | Competitive differentiation. Why us vs alternatives. |
| Email 4 | Low-friction CTA. Sandbox access, no commitment. |
| Email 5 | Breakup. Clear "last touch" framing. |
| LinkedIn DM 1 | Direct ask. Short. Reference email + activity. |
| LinkedIn DM 2 | Share a relevant asset (case study, ROI calc, whitepaper). |

Full copy templates live in `templates/email-sequences/` and `templates/linkedin-sequences/`.
