# HeyReach sequence node reference

Used by `heyreach campaigns create` (the `sequence` field) and `heyreach campaigns update-sequence`.

## Tree shape

A sequence is a **tree of nodes**. The root node is the first action taken on each lead. The implicit
`START` node is never included — the root *is* the first real action.

Each node has:

| Field | Required | Notes |
|---|---|---|
| `nodeType` | yes | One of the types below |
| `payload` | depends | Shape depends on `nodeType` |
| `actionDelay` | **yes (non-root)** | Integer `0`–`100`, paired with `actionDelayUnit`. Wait **before** this node runs. Must resolve to **≥ 3 hours and ≤ 500 days** on every non-root node (including `END`); only the root node may be `0` |
| `actionDelayUnit` | no | `"HOUR"` or `"DAY"` |
| `conditionalNode` | depends | The **positive / true** branch (connection accepted, is-connection = true, email found, reply received) |
| `unconditionalNode` | depends | The **negative / continue** branch (not accepted, not connected, not found, no reply) — or simply "next" for linear nodes |
| `externalReference` | no | Your own tracking ID, ≤ 100 chars |

## Node types

| nodeType | Branches | Payload |
|---|---|---|
| `CONNECTION_REQUEST` | **both** — `conditionalNode` = accepted, `unconditionalNode` = not accepted | **`payload` object required** (omitting it fails). `messages[]` (≤300 chars each; use `[]` for a blank note, which often outperforms), `fallbackMessage`, `toBeWithdrawnAfterDays` (≥14, optional) |
| `MESSAGE` | `unconditionalNode` = continue; `conditionalNode` = reply path, **must be `END`** | `messages[]` (≥1, ≤8000 chars each), **`fallbackMessage` required** |
| `INMAIL` | same as `MESSAGE` | `messages[]` of `{subject ≤200, message ≤1900}`, **`fallbackMessage` required** `{subject, message}` |
| `VIEW_PROFILE` | `unconditionalNode` only | none |
| `FOLLOW` | `unconditionalNode` only | none |
| `LIKE_POST` | `unconditionalNode` only | `reactionType` (`LIKE`/`CELEBRATE`/`SUPPORT`/`FUNNY`/`LOVE`/`INSIGHTFUL`/`CURIOUS`), `randomReaction` (bool), `reactBefore` (`DAY1`/`DAY3`/`WEEK1`/`WEEK2`/`MONTH1`/`MONTH3`, default `MONTH1`), `skipDelayIfCannotLike` (bool) |
| `FIND_EMAIL` | **both** — `conditionalNode` = found, `unconditionalNode` = not found | none |
| `CHECK_IS_CONNECTION` | **both** required | none |
| `CHECK_IS_OPEN_PROFILE` | **both** required | none |
| `SEND_LEAD_TO_INSTANTLY` | `unconditionalNode` only | `instantlyResourceId` (UUID), `resourceType` (`LIST`/`CAMPAIGN`) |
| `SEND_LEAD_TO_SMARTLEAD` | `unconditionalNode` only | `smartLeadCampaignId` (≥1) |
| `SEND_LEAD_TO_BISON` | `unconditionalNode` only | `bisonCampaignId` (≥1) |
| `END` | leaf | none — terminates a branch |

## Validation rules (enforced by the API)

- **Every branch must terminate in an `END` node.**
- `CONNECTION_REQUEST`, `CHECK_IS_CONNECTION`, `CHECK_IS_OPEN_PROFILE`, `FIND_EMAIL` → require **both** branches.
- `MESSAGE` / `INMAIL` → `unconditionalNode` is the continue path; `conditionalNode` (reply) must be `END`.
- `VIEW_PROFILE`, `FOLLOW`, `LIKE_POST`, `SEND_LEAD_TO_*` → `unconditionalNode` only.
- **Every non-root node needs a delay ≥ 3 hours and ≤ 500 days** (e.g. `actionDelay: 3, actionDelayUnit: "HOUR"`, or `1 DAY`). The default `0` is rejected — **including on `END` nodes**. Only the root may be `0`.
- **`CONNECTION_REQUEST` must include a `payload` object** — use `"payload": { "messages": [] }` for a blank note.
- **`MESSAGE` and `INMAIL` must include a `fallbackMessage`** — always, even with no variables.

> ⚠️ The last three rules were confirmed by **live API testing (2026-06-08)** and are **stricter than the CLI's own `--help` examples**, which omit `END` delays, the CR payload, and message fallbacks — those examples are rejected by the server. `campaigns create` and `update-sequence` apply identical validation.

## Personalization variables

Tokens are **single-brace, all-caps**: `{FIRST_NAME}`, `{LAST_NAME}`, `{COMPANY}`, `{POSITION}`,
`{INDUSTRY}`, `{LOCATION}`, `{MY_FIRST_NAME}`, `{MY_LAST_NAME}`, plus any **custom field** you imported
with the lead. A token that doesn't match this exact format appears as raw text in the sent message.

- `fallbackMessage` is **required on every `MESSAGE` / `INMAIL`** (the API rejects messages without one). It
  should read naturally **without** the variable — not just the message with the token deleted.
- When a lead replies, HeyReach automatically stops the sequence for that lead. Design the reply
  (`conditionalNode`) path as `END`.
