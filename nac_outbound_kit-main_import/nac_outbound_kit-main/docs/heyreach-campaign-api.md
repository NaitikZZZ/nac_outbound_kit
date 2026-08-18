# HeyReach Campaign API 
End-to-end test flow for the Campaign Configuration API. Run each step in order — later steps depend on the campaignId returned by step 1.
---

### What a campaign is
A campaign = four things glued together. Configure all four, then activate.
| Piece | Where it's set | What it is |
| Lead list | linkedInUserListId | Who you're reaching |
| Sender account(s) | linkedInAccountIds | Which LinkedIn account sends. Multiple rotate automatically |
| Schedule | schedule object | Which days/hours the campaign runs |
| Sequence | sequence object | The flowchart of steps each lead walks through |
Until activated, the campaign sits in DRAFT and does nothing.

### Sender accounts — the linkedInAccountIds field
The LinkedIn accounts that do the actual sending. Updated via UpdateAccounts.
| Field | Type | Notes |
| linkedInAccountIds | int[] | 1–100 account IDs. All must exist and be authorized |
| Rule | Detail |
| Rotation | Multiple senders automatically rotate across leads — built-in anti-duplication |
| Replacement | UpdateAccounts is a full replacement, not a merge. Anything not in the new list is removed |
| Paused campaigns | Removing a sender stops any in-flight leads assigned to that sender — they can't be resumed |
| Disconnected account | Fails with "invalid auth" — reconnect in HeyReach UI first |

### Schedule — the schedule object
When the campaign is allowed to send. Everything paused outside this window.
| Field | Example | Notes | Type |
| dailyStartTime | "09:00:00" | Must be before dailyEndTime. Max "24:00:00" | TimeSpan |
| dailyEndTime | "17:00:00" | Must be after dailyStartTime | TimeSpan |
| timeZoneId | "America/New_York" | All times interpreted in this zone | IANA string |
| enabledMonday … enabledFriday | true | Default true | bool |
| enabledSaturday, enabledSunday | false | Default false | bool |
| startDate | "2026-05-01" | Future start. If null or past → starts immediately on activation. Locked after first activation | date or null |
| endDate | "2026-12-31" | Campaign auto-stops on this date. Must be after startDate | date or null |
| Detail | Rule |
| At least one enabled* must be true | At least one day |
| Full replacement. Sends SCHEDULED campaigns back to DRAFT | UpdateSchedule |

### Settings — the UpdateSettings fields
Name, lead list, and exclusion filters (skip certain leads).
| Type | Field | Notes |
| string, 1–50 chars | name | Campaign name |
| long | linkedInUserListId | The lead list. Locked after first activation |
| long or null | excludeListId | A separate list of leads to always skip. Must not equal linkedInUserListId |
| bool | excludeContactedFromOtherCampaigns | Skip leads already in any other campaign |
| bool | excludeHasOtherAccConversations | Skip leads with existing conversations from other accounts |
| bool | excludeContactedFromSenderInOtherCampaign | Skip leads the same senders have already touched in other campaigns |
All three exclude* booleans default to false — no filtering unless you opt in.

### What a sequence is
A sequence = a flowchart, not a straight line. Leads walk down it branch by branch.
| Term | Meaning |
| Node | One box in the flowchart (an action or a check) |
| Action node | Does something on LinkedIn (send connection, message, view profile…) |
| Check node | Asks a yes/no question about the lead, then branches |
| END node | "Stop here for this lead." Every branch must end in one |

### Conditional vs unconditional
Every non-END node points to the next node via one or two fields:
| Field | Meaning |
| unconditionalNode | Default / continue / "the thing didn't happen" path |
| conditionalNode | "The thing DID happen" path — accepted / replied / found |
What the "thing" is depends on the node:
| conditionalNode fires when… | unconditionalNode fires when… | Node |
| Lead accepted the invite | Still pending / never accepted | CONNECTION_REQUEST |
| Email was found | Email not found | FIND_EMAIL |
| Lead is a 1st-degree connection | Not a connection | CHECK_IS_CONNECTION |
| Lead has an open profile | Doesn't have one | CHECK_IS_OPEN_PROFILE |
| Lead replied — must route to END | No reply yet — continue | MESSAGE |
| Lead replied — must route to END | No reply yet — continue | INMAIL |
| (no conditional — just run and continue) | Always runs | VIEW_PROFILE, FOLLOW, LIKE_POST, all SEND_LEAD_TO_* |

### What each node does
| One-liner | Node |
| Send connect invite. Branches on accepted vs not | CONNECTION_REQUEST |
| Send DM (1st-degree only) | MESSAGE |
| Send InMail (paid, or free on open profiles). Has subject + body | INMAIL |
| Silent profile view. Good warm-up step | VIEW_PROFILE |
| Follow the lead (they get a notification) | FOLLOW |
| React to their recent post (7 reaction types) | LIKE_POST |
| Try to find their business email. Branches on found/not found | FIND_EMAIL |
| "Already connected?" branch | CHECK_IS_CONNECTION |
| "Open profile?" branch. Gate before INMAIL to save credits | CHECK_IS_OPEN_PROFILE |
| Hand off to Instantly (email) | SEND_LEAD_TO_INSTANTLY |
| Hand off to SmartLead | SEND_LEAD_TO_SMARTLEAD |
| Hand off to EmailBison | SEND_LEAD_TO_BISON |
| Stop. Every branch needs one | END |

### A real example, walked step by step
The flow:
```plain text
Lead enters
    │
    ▼
┌───────────────────────────────────┐
│ Piece 1: CONNECTION_REQUEST       │
│ "Hi {FIRST_NAME}, …"              │
│ wait 3 DAY                        │
└─────┬──────────────────┬──────────┘
      │ accepted         │ not accepted
      ▼                  ▼
┌────────────────┐   ┌──────────┐
│ Piece 2:       │   │ Piece 4: │
│ MESSAGE        │   │ END      │
│ wait 1 DAY     │   └──────────┘
└──────┬─────────┘
       ▼
┌──────────┐
│ Piece 3: │
│ END      │
└──────────┘
```
How the pieces nest:
---
Piece 1 — send the connection request
```json
{
  "nodeType": "CONNECTION_REQUEST",
  "actionDelay": 3,
  "actionDelayUnit": "DAY",
  "payload": {
    "messages": ["Hi {FIRST_NAME}, would love to connect!"],
    "fallbackMessage": "Hi, would love to connect!",
    "toBeWithdrawnAfterDays": 30
  },
  "externalReference": "step-1-connect"
}
```
---
Piece 2 — the "accepted" path: send a message
```json
"conditionalNode": {
  "nodeType": "MESSAGE",
  "actionDelay": 1,
  "actionDelayUnit": "DAY",
  "payload": {
    "messages": ["Thanks for connecting, {FIRST_NAME}!"],
    "fallbackMessage": "Thanks for connecting!"
  },
  "externalReference": "step-2-message"
}
```
---
Piece 3 — end the "accepted" path
Nests inside Piece 2 as its unconditionalNode.
```json
"unconditionalNode": {
  "nodeType": "END",
  "actionDelay": 3,
  "actionDelayUnit": "HOUR"
}
```
---
Piece 4 — end the "not accepted" path
Nests inside Piece 1 as its unconditionalNode. Same shape as Piece 3.
```json
"unconditionalNode": {
  "nodeType": "END",
  "actionDelay": 3,
  "actionDelayUnit": "HOUR"
}
```