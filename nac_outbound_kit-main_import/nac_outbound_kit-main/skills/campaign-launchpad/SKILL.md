---
name: heyreach-campaign-launchpad
description: |
  Build and launch a complete HeyReach LinkedIn campaign end-to-end via the CLI — from a lead source (a CSV file or an existing HeyReach list) to a running campaign. Use when the user wants to create a campaign, launch outreach, "spin up"/"set up"/"start" a campaign, build a new LinkedIn sequence campaign, go from a CSV of leads to a live campaign, or configure senders/schedule/sequence/exclusions and start sending. Handles lead-list creation, CSV import with field mapping, sequence selection, schedule, sender assignment, exclusion settings, a pre-launch checklist, and starting (or scheduling) the campaign. Pairs with the heyreach-sequence-templates skill.
---

# HeyReach Campaign Launchpad

Take a customer from "here are my leads" to a **live, well-configured campaign** in one guided flow. This
skill orchestrates the HeyReach CLI: lead list → sequence → schedule → senders → exclusions → pre-flight → launch.

## Triggers

"spin up / set up / launch / create a campaign", "build a campaign from this CSV", "start outreach to this
list", "turn this list into a LinkedIn campaign", "launch a sequence to these leads" — any request that goes
from a set of leads to live LinkedIn outreach.

Use a different path when the user only wants to **design a sequence** (→ heyreach-sequence-templates), only
wants to **import leads** into a list (→ `heyreach lists` commands), or wants to **edit a campaign that's
already live** (pause it first — ACTIVE campaigns reject edits).

## Set expectations

This skill takes real actions from real LinkedIn accounts on real people. Before each commit point, give the
user a brief, plain-spoken heads-up — deadpan, no hype, one line is enough:

- **Before importing leads:** "Importing <N> leads into list '<name>'."
- **Before launching:** "Launching '<campaign>' on <N> sender(s). First connection requests go out in the
  next working-hours window (<timezone>), ~<M>/day per sender."

Never launch without the pre-flight checklist (Step 6) passing.

## Prerequisites

```bash
export HEYREACH_API_KEY=your_key_here      # workspace API key
heyreach auth check --api-key $HEYREACH_API_KEY
```

You also need **at least one connected, authenticated LinkedIn sender**. List them and confirm health:

```bash
heyreach li-accounts list --api-key $HEYREACH_API_KEY
```

Use only senders with `"authIsValid": true`. For InMail / Sales-Navigator sequences, the sender also needs
`"isValidNavigator": true`. Note the account `id`s you'll use.

## The flow

Work through these in order. Confirm choices with the user as you go; never launch without the pre-flight check.

### 1. Get the leads in

**Option A — CSV file.** Create a list, then import the rows.

```bash
heyreach lists create --api-key $HEYREACH_API_KEY --name "Q2 SaaS Founders"
# Known CLI quirk: this prints an unmarshal error ("...into int32") even though the list IS created.
# Grab the id from the error body, or look it up:
#   heyreach lists list --api-key $HEYREACH_API_KEY --keyword "Q2 SaaS Founders"
```

Parse the CSV (Read it or use a quick script) and map columns to the lead schema:

| CSV column (typical headers) | Lead field |
|---|---|
| LinkedIn URL / Profile / profileUrl | `profileUrl` **(required — the identifier)** |
| First Name | `firstName` |
| Last Name | `lastName` |
| Company | `companyName` |
| Title / Role / Position | `position` |
| Email | `emailAddress` |
| Location | `location` |
| **any other column** | `customUserFields: [{ "name": "...", "value": "..." }]` → usable as a `{VARIABLE}` |

Then add leads **in batches of ≤ 100** per call:

```bash
heyreach lists add-leads --api-key $HEYREACH_API_KEY --body '{
  "listId": 300,
  "leads": [
    { "profileUrl": "https://linkedin.com/in/jane", "firstName": "Jane", "lastName": "Smith",
      "companyName": "Acme", "position": "VP Eng",
      "customUserFields": [{ "name": "Trigger", "value": "just raised Series B" }] }
  ]
}'
```

**Option B — existing HeyReach list.** Find and inspect it; you don't re-import.

```bash
heyreach lists list --api-key $HEYREACH_API_KEY --keyword "Q2 SaaS"   # find the id
heyreach lists get --api-key $HEYREACH_API_KEY --id 300               # confirm it's a USER_LIST with leads
heyreach lists custom-fields --api-key $HEYREACH_API_KEY --id 300     # see which {VARIABLES} are available
```

> **Check connection degree.** If the list contains 1st-degree connections, a sequence that starts with a
> connection request will fail them. Pick the sequence accordingly (next step).

### 2. Pick the sequence

Use the **heyreach-sequence-templates** skill to choose and fill in a sequence that matches the list's
connection degree (connector / message-first / warm-up / mixed-degree / InMail). You'll pass the resulting
sequence JSON in step 5. Read that skill's `references/node-reference.md` for the rules.

### 3. Decide the schedule

Match the audience's business hours. Defaults are Mon–Fri 09:00–17:00 UTC; override timezone and days:

```json
{ "dailyStartTime": "09:00:00", "dailyEndTime": "17:00:00", "timeZoneId": "America/New_York",
  "enabledMonday": true, "enabledTuesday": true, "enabledWednesday": true,
  "enabledThursday": true, "enabledFriday": true }
```

To launch on a future date, add `"startDate": "YYYY-MM-DD"` (creates a SCHEDULED campaign). Add `endDate` to auto-stop.

### 4. Choose senders + set safe limits

From step 0, pick valid senders. Guidance to share with the user:
- **15–25 connection requests/day per sender** (10–15 for new/un-warmed accounts). Avoid pushing toward 40.
- **Scale with more senders, not higher limits** — HeyReach rotates leads across all assigned senders.
- **≤ 2 active campaigns per sender** — daily limits are shared per account, not per campaign.

### 5. Create the campaign (DRAFT)

Assemble everything into one `create` call. Building the body with `jq` keeps the JSON valid when you inject
the sequence:

```bash
heyreach campaigns create --api-key $HEYREACH_API_KEY --body "$(jq -n \
  --arg name "Q2 SaaS Founders" \
  --argjson listId 300 \
  --argjson accountIds '[99,100]' \
  --argjson seq '{ "nodeType": "CONNECTION_REQUEST",
      "payload": { "messages": [] },
      "conditionalNode": { "nodeType": "MESSAGE", "actionDelay": 1, "actionDelayUnit": "DAY",
        "payload": { "messages": ["Thanks for connecting, {FIRST_NAME}!"], "fallbackMessage": "Thanks for connecting!" },
        "conditionalNode": { "nodeType": "END", "actionDelay": 3, "actionDelayUnit": "HOUR" },
        "unconditionalNode": { "nodeType": "END", "actionDelay": 3, "actionDelayUnit": "DAY" } },
      "unconditionalNode": { "nodeType": "END", "actionDelay": 7, "actionDelayUnit": "DAY" } }' \
  '{ name: $name, linkedInUserListId: $listId, linkedInAccountIds: $accountIds,
     excludeContactedFromOtherCampaigns: true, excludeHasOtherAccConversations: true,
     excludeContactedFromSenderInOtherCampaign: false,
     schedule: { dailyStartTime: "09:00:00", dailyEndTime: "17:00:00", timeZoneId: "America/New_York",
       enabledMonday: true, enabledTuesday: true, enabledWednesday: true, enabledThursday: true, enabledFriday: true },
     sequence: $seq }')"
# → { "campaignId": 12345 }   (status: DRAFT)
```

Swap the inline `$seq` for a filled-in template from heyreach-sequence-templates. **Exclusion options** —
set these to protect sender reputation and avoid double-contacting:
`excludeContactedFromOtherCampaigns`, `excludeHasOtherAccConversations`,
`excludeContactedFromSenderInOtherCampaign`, and `excludeListId` (a list of people to skip).

> **Editing instead of creating?** On a DRAFT/SCHEDULED/PAUSED campaign use the piecewise commands:
> `campaigns update-sequence`, `update-schedule`, `update-accounts --campaign-id N --account-ids a,b`,
> `update-settings`. (ACTIVE/COMPLETED campaigns reject edits.)

### 6. Pre-flight checklist (do not skip)

Confirm each item before launch:

- [ ] Lead list is **targeted**, not a broad generic search
- [ ] **Connection degree** is known and the sequence matches it
- [ ] **Exclusions** configured (prior contacts / conversations / exclude list)
- [ ] **Daily limits** conservative (10–15 new accounts; 15–35 established)
- [ ] **Working hours, timezone, active days** match the audience's location
- [ ] Total **delay after the connection request ≥ 7 days** on the not-accepted side
- [ ] **`fallbackMessage` set** on every node whose messages use variables
- [ ] Variables use the correct format — single-brace, all-caps, e.g. `{FIRST_NAME}`, `{COMPANY}` (see node-reference)
- [ ] **≤ 2 campaigns** running per sender
- [ ] All chosen senders are **connected** (`authIsValid: true`)

### 7. Launch (or schedule)

```bash
heyreach campaigns start --api-key $HEYREACH_API_KEY --id 12345
```

If you set a future `startDate`, the campaign is already SCHEDULED and will start itself; `start` launches it now.

### 8. Verify

```bash
heyreach campaigns get --api-key $HEYREACH_API_KEY --id 12345
```

Expect status `STARTING` then `IN_PROGRESS`. Track `progressStats` over time
(`totalUsersInProgress`, `totalUsersFinished`, `totalUsersFailed`). For a true smoke test, launch to **1–2
leads first**, confirm the message renders with real personalization (no raw `{TOKENS}`), then add the rest.

Then report a compact **launch summary** back to the user:

```
Campaign:    <name>  (id <id>)
Status:      IN_PROGRESS
Lead list:   <name>  (<N> leads)
Senders:     <count> — <names>
Schedule:    <days> <start>–<end> <timezone>
Sequence:    <first action> → … (<step count> steps)
Exclusions:  <which exclusion options are on>
Next:        first actions go out during the next working-hours window
```

## Status & edit rules (gotchas)

- `start` works only on **DRAFT** or **SCHEDULED**; `resume` only on **PAUSED**; `pause` only on **IN_PROGRESS**.
- Edits (`update-*`) work only on **DRAFT / SCHEDULED / PAUSED**. On PAUSED, the sequence *structure* is locked
  (you can edit delays and payloads, not the tree shape).
- After a campaign has started once, **`linkedInUserListId` and `startDate` can no longer change**.
- The lead list must be a **`USER_LIST`** (the type `lists create` makes). Max **100 leads per add-leads call**.
- `campaigns create` / `update-sequence` validate the sequence tree server-side; fix any reported node and resubmit.
