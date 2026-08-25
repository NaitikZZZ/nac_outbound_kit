# Smartlead API Gaps — Feature Requests to File with Smartlead Support

> Confirmed against Smartlead's public API (`server.smartlead.ai/api/v1`) and `llms.txt` as of 2026-08-25. Each item below can currently only be set by hand in the Smartlead dashboard, once per campaign or account, because there is no documented endpoint for it. That's what blocks us from fully automating campaign creation end to end.

## 1. Private infrastructure / dedicated sending server selection

- **What it does:** assigns which of the private sending servers a campaign uses. Our standard is all 4 servers selected on every campaign.
- **Where it lives today:** Campaign > Settings > General > Private Infrastructure
- **What we need:** an endpoint to read/write the assigned server(s) on a campaign (e.g. `GET/PATCH /campaigns/{id}/infrastructure`)

## 2. AI-based lead reply categorization

- **What it does:** turns on Smartlead's AI auto-categorization of replies, and controls which categories are active. Our standard is all categories on, including "Do Not Contact".
- **Where it lives today:** Campaign > Settings > AI Categorization
- **What we need:** an endpoint to enable/disable auto-categorization and set the active category list per campaign

## 3. Out-of-office (OOO) handling

- **What it does:** three toggles plus one numeric field — exclude OOO replies from reply-rate metrics; auto-restart a lead after they return from OOO; a re-activation-after-delay toggle (marked "deprecated" in the UI but still functional); and the number of days to wait before re-activating (our standard: 7).
- **Where it lives today:** Campaign > Settings > Out of Office Handling
- **What we need:** an endpoint to read/write these four fields per campaign

## 4. HubSpot Integration toggle

- **What it does:** turns on/off syncing a campaign's activity (opens, replies, etc.) into HubSpot.
- **Where it lives today:** Campaign > Settings > Integrations > HubSpot
- **What we need:** an endpoint to enable/disable per campaign

## 5. ESP matching

- **What it does:** matches sending infrastructure/warmup behavior to the lead's email service provider (Gmail, Outlook, etc.) for better deliverability. Our standard is on.
- **Where it lives today:** Campaign > Settings > General > ESP Matching
- **What we need:** an endpoint to toggle per campaign

## 6. Tag creation & assignment (email accounts / campaigns)

- **What it does:** create tags (e.g. our region tags like "India Email Accounts") and assign them to email accounts or campaigns.
- **What's already there:** `GET /email-accounts` returns a read-only `tags` array.
- **What's missing:** no endpoint to create a tag, or to assign/unassign an existing tag to an account or campaign.
- **Where it lives today:** Settings > Tag Manager (create); per-account Edit > Management, or a campaign's "..." menu (assign)
- **What we need:** endpoints to create a tag, and to assign/unassign a tag to an email account or campaign

---

## Already covered by the API (no ask needed)

Campaign create, sequence steps (`/campaigns/{id}/sequences`), schedule (`/campaigns/{id}/schedule`), lead upload (`/campaigns/{id}/leads`), sender account attach (`/campaigns/{id}/email-accounts`), and most of `/campaigns/{id}/settings` — including `track_settings` (don't-track opens/clicks), `stop_lead_settings`, `follow_up_percentage`, and `add_unsubscribe_tag`.

---

## Ready-to-send summary

> We're automating Smartlead campaign creation end to end and have hit a handful of settings with no API coverage, so we have to set them by hand on every campaign: (1) private infrastructure / server selection, (2) AI lead reply categorization (enable + category list), (3) out-of-office handling (the three toggles + delay days), (4) the HubSpot Integration toggle, (5) ESP matching, and (6) tag creation/assignment on email accounts and campaigns. Could these be exposed via the API, or is there a roadmap item we could track?
