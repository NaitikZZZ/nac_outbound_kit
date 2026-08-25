# HeyReach API Reference

> Base URL: `https://api.heyreach.io/api/public`
> Auth: `X-API-KEY` header
> Rate limits: 300 API requests/min (shared); 100 leads per list upload; 20 connections / 50 messages per day per sender
>
> **Full endpoint list:** see [`heyreach-api-reference.md`](heyreach-api-reference.md) - auto-generated from the live Postman collection by `scripts/09_heyreach_api_tracker.py`. This file below is the curated, hand-written playbook (cadence, merge tags, gotchas).

## Key Endpoints for This Kit

### Create empty list

```
POST /list/CreateEmptyList
Headers: X-API-Key: <key>
Body: {"name": "P1_EVENTS_...", "listType": "USER_LIST"}
Response: {"id": 614694, "name": "...", ...}
```

### Add leads to list (batch of 100)

```
POST /list/AddLeadsToListV2
Headers: X-API-Key: <key>
Body:
{
  "listId": 614694,
  "leads": [
    {
      "profileUrl": "https://www.linkedin.com/in/first-last",
      "firstName": "First",
      "lastName": "Last",
      "emailAddress": "first@company.com",
      "companyName": "Company",
      "position": "Job Title"
    }
  ]
}
Response: {"addedLeadsCount": 100, "updatedLeadsCount": 0, "failedLeadsCount": 0}
```

### Other common endpoints (verified paths)

| Purpose | Endpoint |
|---------|----------|
| List all campaigns | `POST /campaign/GetAll` |
| Get campaign details | `GET /campaign/GetById` |
| Pause campaign | `POST /campaign/Pause` |
| Resume campaign | `POST /campaign/Resume` |
| Start (activate DRAFT) campaign | `POST /campaign/StartCampaign` |
| Add leads to campaign | `POST /campaign/AddLeadsToCampaignV2` |
| Get LinkedIn sender accounts | `POST /li_account/GetAll` |
| Send inbox message | `POST /inbox/SendMessage` |
| Get conversations | `POST /inbox/GetConversationsV2` |

> Older versions of this table listed `GET /campaigns/GetAll`, `/campaigns/Get/{id}` and `GET /LinkedInAccount/GetAll` - those paths are wrong. Use the ones above, and see [`heyreach-api-reference.md`](heyreach-api-reference.md) for the complete, always-current list.

---

## Merge Tags

**Correct syntax confirmed live (2026-08-24): single curly braces, uppercase.** The double-brace lowercase style below (`{{first_name}}`) is what Smartlead uses, not HeyReach — pasting it into a HeyReach DM/InMail leaves the literal text unrendered. Confirmed by comparing a campaign's `GetCampaignSequence` output before and after a manual fix in the HeyReach UI.

| Tag | Meaning |
|-----|---------|
| `{FIRST_NAME}` | Prospect first name |
| `{COMPANY}` | Prospect company (not `{COMPANY_NAME}`) |

Only these two were confirmed live so far. Treat any other tag (last name, position) as unverified until seen working in a real campaign — don't assume it follows the same pattern without checking.

---

## Recommended Standard Cadence

**Superseded by `docs/heyreach-default-workflow.md`** (extracted from a live campaign, 2026-08-25): a `CHECK_IS_CONNECTION` branch, profile visit + like + no-note connect for not-yet-connected leads, then a 4-message DM sequence (with a second profile visit before the last DM) for both branches, stop-on-reply on every message. See that doc for the full flowchart and delays.

---

## Campaign Settings (Configure in HeyReach UI)

- **Daily limits:** 20 connection requests, 50 messages per sender per day
- **Working hours:** Match sender timezone, 9am-6pm
- **Working days:** Mon-Fri only
- **Skip if already connected:** Yes (start from DM step for existing connections)
- **Stop on reply:** Yes
- **Navigator / Recruiter senders:** Available for Sales Navigator / Recruiter InMail

---

## Rate Limit Gotchas

1. **Per-account daily limits** - LinkedIn enforces this, HeyReach respects it. Budget sends accordingly.
2. **Account warmup** - New LinkedIn accounts should warm up for 2-3 weeks before full-volume outreach.
3. **Duplicate leads** - HeyReach dedupes across lists automatically.
4. **Invalid profile URLs** - anything not starting with `https://www.linkedin.com/in/` or `http://linkedin.com/in/` is rejected.

---

## Batch Lead Upload Tips

- Keep batches at 50-100 leads max
- Add 1 second sleep between batches
- Minimum fields: `profileUrl`, `firstName`, `lastName`
- Include `emailAddress`, `companyName`, `position` if available for better merge-tag personalization
