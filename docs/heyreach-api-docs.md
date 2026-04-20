# HeyReach API Reference

> Base URL: `https://api.heyreach.io/api/public`
> Auth: `X-API-Key` header
> Rate limits: 100 leads per list upload, 20 connections / 50 messages per day per sender

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

### Other endpoints (mostly used via HeyReach UI)

| Purpose | Endpoint |
|---------|----------|
| List all campaigns | `GET /campaigns/GetAll` |
| Get campaign details | `GET /campaigns/Get/{id}` |
| Pause / resume campaign | `POST /campaigns/Pause/{id}` or `POST /campaigns/Resume/{id}` |
| Get LinkedIn accounts | `GET /LinkedInAccount/GetAll` |
| Send message | `POST /inbox/SendMessage` |

---

## Merge Tags

HeyReach supports these tags inside DM and InMail messages:

| Tag | Meaning |
|-----|---------|
| `{{first_name}}` | Prospect first name |
| `{{last_name}}` | Prospect last name |
| `{{company_name}}` | Prospect company |
| `{{position}}` | Prospect job title |

---

## Recommended Standard Cadence (5 Steps)

| Day | Step | Configuration |
|-----|------|---------------|
| D1 | Visit Profile | Automatic, no message |
| D2 | Like Post | Most recent post |
| D4 | Send Connection Request | NO note - higher acceptance rates |
| D7 | DM (if connected) or InMail (if not) | Main pitch message |
| D10 | Follow-up DM | Value-add, asset share, breakup |

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
