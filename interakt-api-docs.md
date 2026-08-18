# Interakt API Documentation

> Source: `https://documenter.getpostman.com/view/14760594/2sA2r7zibM` (Postman collection: "Interakt Public APIs")
> Public APIs are **not available on the Starter plan** — Growth, Advanced, or Enterprise required.

## Base URL
```
https://api.interakt.ai/v1/public
```

## Authentication
All requests require the `Authorization` header:
```
Authorization: Basic {{YOUR_API_KEY}}
```
Get your API key from: **Interakt Dashboard → Developer Settings**

## Rate Limits
| Plan | Limit |
|------|-------|
| Growth | 300 requests/minute |
| Advanced | 600 requests/minute |
| Enterprise | Configurable per Meta's allowed rate limit |

429 response: `{"message": "Rate limit exceeded for this resource"}` — implement retry with exponential backoff.

---

## Track APIs

### POST `/track/users/`
Create or update a customer profile. Same trait sent twice **replaces** the previous value.

**Body:**
```json
{
  "phoneNumber": "9999999999",
  "countryCode": "+91",
  "traits": {
    "name": "Harsh",
    "merchant_location": "IN",
    "whatsapp_opted_in": true,
    "account_owner_email_crm": "abc@gmail.com"
  },
  "add_to_sales_cycle": true,
  "createdAt": "2025-03-27T13:26:52.926Z",
  "tags": ["sample-tag-1", "sample-tag-2"]
}
```
- `userId` — optional custom user ID
- `countryCode` + `phoneNumber` **or** `fullPhoneNumber` (not both) — required
- `traits` — flat key-value JSON of customer attributes
- `tags` — list of tag strings

**Response (202):**
```json
{ "result": true, "message": "Customer with <id> updated successfully" }
```

---

### POST `/track/events/`
Log an event for a user. Same event sent at different times **does not** replace previous entries — represented on a timeline.

**Body:**
```json
{
  "userId": "12035448-36a0-3aa24",
  "phoneNumber": "9999999999",
  "countryCode": "+91",
  "event": "Product Added To Cart",
  "traits": {
    "productName": "Shoes",
    "quantity": 2,
    "price": 500,
    "currency": "INR"
  }
}
```

**Response (201):**
```json
{ "result": true, "message": "Event created successfully", "id": "730ec207-..." }
```

---

## Customer APIs

### POST `/apis/users/?offset=0&limit=100`
Fetch users in bulk with pagination + trait filters.

**Body:**
```json
{
  "filters": [
    { "trait": "created_at_utc", "op": "gt", "val": "2021-09-08T11:35:47.089Z" },
    { "trait": "created_at_utc", "op": "lt", "supr_op": "and", "val": "2021-09-08T11:40:47.089Z" }
  ]
}
```
Response includes `total_customers`, `has_next_page`, and a `customers[]` array with full trait/address data.

### GET `/apis/users/phone_number/{phoneNumber}`
### GET `/apis/users/id/{userId}`
Fetch a single customer by phone number or Interakt user ID. Same response shape as bulk (`data.customers[]`), including `tags`, `tag_names`, and `traits`.

---

## Send Message APIs
### POST `/message/`
One endpoint, `type` field determines message shape: `Text`, `Image`, `Audio`, `Video`, `Document`, `Sticker`, `Button`, `List`, or `Template` (see below).

**Text example:**
```json
{
  "fullPhoneNumber": "919999999999",
  "callbackData": "some_callback_data",
  "type": "Text",
  "data": { "message": "This msg is sent via API" }
}
```

**Image/media example:**
```json
{
  "countryCode": "+91",
  "phoneNumber": "9999999999",
  "type": "Image",
  "data": { "message": "This is a test", "mediaUrl": "MEDIA_URL" }
}
```

**Response (201):**
```json
{ "result": true, "message": "Message queued for sending via Interakt. Check webhook for delivery status", "id": "..." }
```

---

## Send Template APIs
### POST `/message/` with `"type": "Template"`
This is the one that matters for cold-outreach-style sends — dispatches an approved WhatsApp template with placeholder values.

```json
{
  "countryCode": "+91",
  "phoneNumber": "9999999999",
  "campaignId": "YOUR_CAMPAIGN_ID",
  "template_category": "utility",
  "callbackData": "some text here",
  "type": "Template",
  "template": {
    "name": "template_name_here",
    "languageCode": "en",
    "headerValues": ["header_variable_value"],
    "bodyValues": ["body_variable_value_1", "body_variable_value_n"]
  }
}
```
- `headerValues` only needed if the template has a text header with a variable — omit for no-header templates.
- Template must already exist and be **APPROVED** (see Get All Templates below) — templates are created/approved separately, not inline with the send.

**Response (201):**
```json
{ "result": true, "message": "Message created successfully", "id": "..." }
```

### GET `/track/organization/templates`
List existing templates (to look up `name`/`languageCode` before sending).

**Query params:** `offset`, `template_name`, `autosubmitted_for`, `approval_status` (e.g. `APPROVED`), `variable_present` (`Yes`/`No`), `language`

**Response (200):**
```json
{
  "count": 1,
  "has_next": false,
  "results": {
    "templates": [
      {
        "id": "ea5258f4-...",
        "name": "test123",
        "language": "en",
        "category": "UTILITY",
        "body": "Hi {{1}},\n\nThis is a test utility template dated {{2}}",
        "approval_status": "APPROVED",
        "variable_present": "Yes"
      }
    ]
  }
}
```

---

## Campaign APIs
### POST `/create-campaign/`
```json
{
  "campaign_name": "Harsh Test",
  "campaign_type": "PublicAPI",
  "template_name": "newtemplate",
  "language_code": "en"
}
```
**Response (201):**
```json
{ "result": true, "message": "Api Campaign Created created successfully", "data": { "campaignId": "...", "name": "Harsh Test", "type": "PublicAPI" } }
```

---

## Chat Assignment API
### POST `/assignment/`
```json
{
  "user_phone_number": "919876543210",
  "agent_email": "test.agent@interakt.ai"
}
```
Note: `user_phone_number` = country code + number concatenated, **no** `+` or spaces.

**Response:**
```json
{ "result": true, "message": "Chat Assigned Successfully" }
```
Status codes: 200 OK, 401 Unauthorized, 400 Bad Request, 500 Server Error.

---

## Not covered here (present in the Postman collection but out of scope until needed)
- Create Template APIs (building new WhatsApp templates programmatically — header variants, carousel, CTA/quick-reply buttons, media upload)
- WhatsApp → SMS Fallback variants of Send Template
- RCS messaging (separate channel, same `/rcs/message/` endpoint, distinct payload shapes)

## Webhooks
**Not part of this Postman collection.** Interakt's webhook setup (Message Status: Sent/Delivered/Read/Failed, and Incoming Message) is configured in the dashboard under Developer Settings, not documented via this API reference. Need to pull those payload schemas separately once we're ready to build the receiver — check the dashboard's webhook config page for a payload example when that's next.
