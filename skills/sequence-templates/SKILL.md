---
name: heyreach-sequence-templates
description: |
  Ready-to-use, best-practice-aligned HeyReach campaign sequence templates (the sequence JSON for `heyreach campaigns create` and `heyreach campaigns update-sequence`), plus copy frameworks and the full node-type / validation reference. Use when the user wants a sequence or flow for a LinkedIn campaign, asks for a "connector sequence", "follow-up sequence", "message-first", "InMail campaign", "warm-up sequence", wants to design, build, or edit a campaign sequence, needs the sequence JSON, or asks which node types, delays, or branches are valid in HeyReach. Pairs with the heyreach-campaign-launchpad skill.
---

# HeyReach Sequence Templates

A library of sequence structures that follow HeyReach's official campaign best practices, plus the rules for building your own.
A sequence is the tree of LinkedIn (and non-LinkedIn) actions a campaign runs on each lead over time.

## Triggers

"give me a connector sequence", "build a follow-up sequence", "design a campaign flow", "message-first /
warm-up / InMail sequence", "what should my sequence look like", "edit / redesign my sequence", or "what node
types / delays / branches are valid in HeyReach?".

Also activates when you're running **heyreach-campaign-launchpad** and need a sequence to apply. For the raw
node rules and validation, point to `references/node-reference.md`.

## How to use a template

1. **Read** `references/node-reference.md` once so the node rules and personalization-variable format are fresh.
2. **Pick** a template below that matches the lead list's connection degree and the goal.
3. **Open** the matching file in `references/sequences/` and **fill in the placeholders** (`<...>` and the
   personalization tokens) with the user's real copy. Keep messages short (3–5 sentences) and lead with value.
4. **Summarize the flow back to the user in plain English before applying** — e.g. "Connect (blank note) →
   on accept, wait 1 day → send message → if no reply after 3 days, follow up; non-accepters get a post-like
   at day 7, then exit." This is the confirmation step — get a yes before writing anything.
5. **Apply** it:
   - On a new campaign — pass it as the `sequence` field of `heyreach campaigns create` (see the launchpad skill).
   - On an existing DRAFT / SCHEDULED / PAUSED campaign:
     ```bash
     heyreach campaigns update-sequence --api-key $HEYREACH_API_KEY \
       --body "$(jq -n --argjson seq "$(cat references/sequences/01-connector-1-followup.json)" \
         '{campaignId: 12345, sequence: $seq}')"
     ```
   - The API validates the tree on submit. If it returns an error, fix the reported node and resubmit.
   - **Heads-up on a PAUSED campaign:** the structure is locked — you can change delays and message payloads,
     but not the tree shape. On DRAFT / SCHEDULED the whole sequence is replaceable.
6. **Test before scaling**: launch to 1–2 leads first and confirm the message renders with real
   personalization (no raw `{TOKENS}`) before relying on the sequence at volume.

## Templates

| File | Use when | Shape |
|---|---|---|
| `01-connector-1-followup.json` | Bread-and-butter cold outreach to 2nd/3rd-degree leads | Connect → (accepted) 1 message |
| `02-connector-2-followup-warm.json` | Cold outreach, want a 2nd touch + keep non-accepters warm | Connect → (accepted) msg → wait → msg; (not accepted) like a post to stay in their feed |
| `03-warmup-engage-first.json` | Higher-acceptance cold outreach — warm the lead before asking | View profile → like post → connect → (accepted) message |
| `04-open-profile-message-first.json` | Mixed list where some are Open Profiles (message free, no connect) | If open profile → message directly; else → connect → message |
| `05-mixed-degree-safe.json` | List mixes 1st-degree (already connected) with 2nd/3rd | If already connected → message directly; else → connect → message |
| `06-inmail.json` | Sales Navigator / InMail outreach (no connection needed) | Single InMail with subject + body |

> **Connection degree matters.** Starting a 1st-degree connection with a `CONNECTION_REQUEST` fails them
> immediately (you're already connected). If the list is mixed, use `05-mixed-degree-safe.json`. If it's all
> 1st-degree, lead with a `MESSAGE`, not a connect.

## Sequence-building rules (the short version)

Full detail in `references/node-reference.md`. The essentials:

- **Every branch ends in `END`.** `conditionalNode` = positive branch (accepted / connected / found / reply);
  `unconditionalNode` = negative-or-continue branch.
- **`CONNECTION_REQUEST`, `CHECK_IS_CONNECTION`, `CHECK_IS_OPEN_PROFILE`, `FIND_EMAIL` need both branches.**
  `VIEW_PROFILE`, `FOLLOW`, `LIKE_POST`, `SEND_LEAD_TO_*` take `unconditionalNode` only.
- **Generous delays after a connection request.** Connections are often accepted 5–7 days out — keep the
  left (not-accepted) side alive 7–12 days total before ending. An engagement action (like a post) there
  triggers a notification and lifts acceptance.
- **Don't repeat the same action type** in one sequence — senders' daily limits are shared across steps, so
  duplicating an action splits throughput.
- **Every `MESSAGE` / `INMAIL` needs a `fallbackMessage`** — required by the API, not just when using variables.
- **Every non-root node needs `actionDelay` ≥ 3 hours** (≤ 500 days), *including `END` nodes* — `0` is rejected. The templates already set these; keep them when editing.
- **`CONNECTION_REQUEST` needs a `payload`** — use `{ "messages": [] }` for a blank note (blank often beats a noted one; if you add a note, make it count, ≤300 chars).

## Copy frameworks

**Connection note (if used):** short, specific, no pitch. Reference something real about them.

**First message (after accept):** acknowledge the connection → one specific, relevant observation →
a low-friction question. Goal is a reply, not a close. 3–5 sentences.

**Follow-up (no reply):** add *new* value (an insight or resource), don't just "bump." Give an easy out.

**InMail:** subject is a real question, not a headline. Body = same value-first structure, kept tight.

## Personalization variables

Use **single-brace, all-caps** tokens: `{FIRST_NAME}`, `{LAST_NAME}`, `{COMPANY}`, `{POSITION}`,
`{INDUSTRY}`, `{LOCATION}`, `{MY_FIRST_NAME}`, `{MY_LAST_NAME}`, plus any custom field imported with the
lead (full list in `references/node-reference.md`). Every variable-using message **must** have a
natural-reading `fallbackMessage`.
