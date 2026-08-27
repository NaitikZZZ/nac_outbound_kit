# Content Agent Rules

Style, format, and copy rules the agent applies when drafting outbound content for this kit. Campaign planning (persona/use-case consolidation, approved content sources, campaign types, pre-launch checklist) is covered in full by [`campaign-content-strategy-sop.md`](campaign-content-strategy-sop.md). Key points:
- One consolidated sequence per persona, not one per use case, use cases and proof points get introduced gradually across the sequence.
- Draw claims only from approved Xoxoday sources (website, product decks, help docs, internal wiki, approved case studies). Never invent a fact, metric, or claim.
- Same core message (theme, proof stack) carries across email and LinkedIn, LinkedIn runs shorter/native to the channel, not a word-for-word copy.
- No one-line emails. Every message stands on its own with enough context and value.
- Use-Case Campaigns (persona/industry/use-case based) are reviewed ~every 6 months; Dynamic Campaigns (job changes, funding, intent signals, hiring, expansion, news) are planned and executed separately since they need current context.

## Punctuation
- Never use em dashes (—) or en dashes (–). Use hyphens, commas, or rewrite.
- Zero exclamation points in cold outbound.

## Step 1 Cold Outbound Email Format
Full rule set: [`cold-outbound-email-sop.md`](cold-outbound-email-sop.md) (Manoj Agarwal SOP, authoritative). Summary:
- No fixed sentence/word count. Complete, substantive introduction, not a thin one. Structured with bullets where a list runs 3+, not dense paragraphs.
- No selling: no stats, no ROI numbers, no feature pitch, no product deep-dive. Positioned purely as an introduction.
- Subject: under 5 words, specific, neutral, no cleverness, no emojis.
- Lead with a concrete, low-effort ask in sentence 1 (e.g. same location/domain, offer to show how a similar problem was solved).
- Xoxoday positioned as a global company (credibility signal, customized to the product), not a name-drop.
- No signature block (Smartlead auto-appends it at the account level).
- Output: subject line, blank line, body. No labels, no explanations.

## Sequencing (Step 2 onward)
- Every email reads as if it's the first, no "as discussed," "following up," "third note," or any sequence-position reference, ever.
- Never imply the sequence is ending ("before I close," "last mail," "closing the loop"). Cadence is open-ended until the prospect responds.
- Under 100 words. No banned phrases. No pitching until the arc calls for it (see SOP section 3). Low-pressure CTA. No dashes. No buzzwords.
- Funnel runs Email -> WhatsApp -> SDR call as a waterfall, not email alone.

## LinkedIn / WhatsApp / Call Scripts
All formatting/banned-phrase rules apply. No sentence-count rule. Same core message as the matching email step (theme, proof stack), just shorter and native to the channel, not pasted word-for-word.
- LinkedIn: no name sign-off at the end (sender profile shows automatically).
- Calls/WhatsApp: include name sign-off.

## Variants
Single variant only, no A/B split. Follow the 7-email arc in `cold-outbound-email-sop.md` section 3 for what content goes in which step. Ask which product/use case if not stated before writing.

## Banned Phrases
"I hope you're doing well", "Impressive background", "Your X caught my attention",
"I'd love to pick your brain", "I know you're busy", "Just checking in",
"Let me introduce myself", "We're the X of Y", "We're disrupting",
"I wanted to reach out", "Would you be open to a quick chat?",
"We help companies like yours", "Thought you might be interested",
"Not sure if you're the right person", "Touching base", "Circling back",
"Quick question" (as filler), "As mentioned in my last email", "This is my final follow-up", "This is my closing note"

## Banned Buzzwords
delve, landscape, leverage, realm, tapestry, navigate (verb), robust,
seamless, seamlessly, cutting-edge, groundbreaking, game-changing, revolutionize,
transform, elevate, unlock, meticulous, intricate, nuanced (unless genuinely needed),
"in today's fast-paced world", "in the ever-evolving", dive into, deep dive,
"it is worth noting", "it is important to note", notably, significantly,
harness, harness the power of, empower, empowering

## Humanizer Pass (always on)
Every drafted email, DM, script, brief, or doc gets a humanizer pass inline before delivery, blunt/Bezos-cadence voice by default:
- Short declarative sentences, mixed lengths. Lead with verb or subject, no "However," / "Moreover," openers.
- Sentence fragments fine. Contractions where natural.
- Specific numbers/names/anecdotes over generic claims. Concrete verbs ("rebuilt" not "transformed").
- No three-item bullet parallelism, no hedge-then-assert, no bow-tie endings ("In essence," / "Ultimately,").
- Max 1-2 bolds per paragraph.

## CSV Output Defaults
- Every output CSV includes `full_name` (first + last) and `company_domain`.
- Confirm `company_domain` resolution with the operator before generating.
- Normalize before any API upload or file send: `first_name` (first token only), `last_name` (strip credentials/suffixes), `company_name` (strip legal suffixes). These feed email merge tags directly, and company-name normalization (via `resolve_company_domains.py`'s cache) is what makes company-name-based email pattern guesses reliable.
- Confirmed 2026-08-28, applies to every export regardless of source channel:
  - HubSpot/email export (`08_export_hubspot_csv.py`) always carries Phone Number and LinkedIn URL alongside email, so a single "holistic" row can be imported to HubSpot.
  - Attempt email enrichment on LinkedIn-sourced leads too (not just LinkedIn URL) so HubSpot workflow triggers can fire on them where possible. This is best-effort, not a gate: if no email is found, still export the prospect with LinkedIn URL only. Never drop a lead from the export just because email enrichment came up empty.
  - WhatsApp/HS import needs the phone split into two columns, not one E.164 string: `08_export_hubspot_csv.py` outputs `Phone Country Code` and `Phone Number (Local)` (see `split_phone()` / `COUNTRY_DIAL_CODES` in that script) alongside the existing combined `Phone Number`.
  - Exclude below-managerial titles (Associate, Executive, Analyst, Coordinator, Specialist, Officer, etc.) from every list before outreach - see `reference/icp-scoring-criteria.md` Disqualification Criteria and `is_non_icp_title()` in `scripts/icp_titles.py`.

## Smartlead Campaign Defaults
Timezone `Asia/Calcutta`, Mon-Fri 9-6, 20 min send interval, 200/day cap, tracking off, ESP matching on, AI auto-categorization on all categories, OOO handling with 7-day restart.

## Apollo Enrichment Defaults
Default to a curated column set for enrichment output (skip internal IDs/postal codes, truncate long multi-value fields like tech stacks) rather than exporting every raw field. Offer a `--full` flag for the rare case the operator wants everything.
