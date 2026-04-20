# Campaign Naming Convention - Xoxoday GTM & Outbound

> Applies to all campaigns in HubSpot, Clay, Smartlead, HeyReach, Interakt, and any other sequencing tool. Use this format every time, across every team (Events, Partnership, API, ABM).

## The Formula

```
PRIORITY _ TEAM _ USECASE _ REGION _ CHANNEL _ POCNAME _ STARTDATE
```

Separator: underscore `_`. No spaces. No other characters.

Order rationale: **Priority** first for instant triage. **Team and use case** for cross-team grouping. **Region** scopes the audience. **Channel** tells you the motion. **POC name** locks in ownership. **Start date** anchors it.

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

**Multi-region rule:** Combine codes with hyphens, alphabetically sorted.
- `KSA-IDN-GCC`
- `IND-US-UKEU`

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

Lowercase first name of campaign owner. No spaces.

| Input | Write as |
|-------|---------|
| Rahul Sharma | `rahul` |
| Priya Nair | `priya` |
| Rahul + Priya (co-own) | `rahul-priya` |

### Start Date

`DDMMMYY` with uppercase three-letter month.

| Date | Format |
|------|--------|
| January 1, 2026 | `01JAN26` |
| April 15, 2026 | `15APR26` |
| November 30, 2026 | `30NOV26` |

---

## Full Examples

| Campaign Name | What It Means |
|---------------|---------------|
| `P0_ABM_DREAM_US_EMAIL_rahul_01JAN26` | ABM, Dream account, US, Email, Rahul, Critical, Jan 1 2026 |
| `P1_EVENTS_PREEVENT_IND_EMAIL-LI_priya_15APR26` | Events, Pre-event, India, Email + LinkedIn, Priya, High, Apr 15 2026 |
| `P2_ABM_BFSI_GCC_LI_arjun_01MAY26` | ABM, BFSI industry, GCC, LinkedIn, Arjun, Medium, May 1 2026 |
| `P1_ABM_INTENT_KSA-IDN-GCC_EMAIL-WA_rahul_10FEB26` | ABM, Intent signal, ROW, Email + WhatsApp, Rahul, High, Feb 10 2026 |
| `P2_PRTNR_FUNDING_US_EMAIL_neha_20MAR26` | Partnership, Funding trigger, US, Email, Neha, Medium, Mar 20 2026 |
| `P3_API_ENT500_UKEU_EMAIL-LI_sam_01JUN26` | API, Employee 500+, UK/EU, Email + LinkedIn, Sam, Low, Jun 1 2026 |
| `P1_ABM_POSTEVENT_IND_WA-CALL_priya_20APR26` | ABM, Post-event, India, WhatsApp + Call, Priya, High, Apr 20 2026 |
| `P0_EVENTS_DREAM_US_EMAIL-LI_rahul-priya_05JAN26` | Events, Dream accounts, US, Email + LinkedIn, Rahul + Priya (co-own), Critical, Jan 5 2026 |

---

## 7 Steps to Name Your Campaign

1. **Set priority** - Board-level (P0), strategic (P1), standard (P2), nurture (P3)
2. **Identify team** - EVENTS / PRTNR / API / ABM
3. **Pick use case** - see Section 3.3. If not listed, use `CUSTOM-[X]`
4. **Define region** - use region code, multi-region hyphenated alphabetically
5. **Choose channel(s)** - single or hyphenated in first-touch order
6. **Add POC name** - lowercase first name, hyphenate if co-owned
7. **Add start date** - `DDMMMYY`

---

## Common Mistakes

- Writing `P1-EVENTS-...` with hyphens instead of underscores (underscores between components, hyphens only within multi-region / multi-channel / co-POC)
- Forgetting the start date
- Using full names (`rahul-sharma`) instead of just first name (`rahul`)
- Lowercase month (`apr26` instead of `APR26`)
- Using "Email" or "LinkedIn" as free text instead of the codes (`EMAIL`, `LI`)
- Using region names like "India" instead of codes (`IND`)

---

*Xoxoday | GTM and Outbound Team | Internal Use Only*
