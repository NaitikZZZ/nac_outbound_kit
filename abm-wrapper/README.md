# ABM Wrapper (rebuild)

Rebuild of the lost `abm-wrapper-backend` tool: upload a prospect/account CSV, walk it
through normalization, domain resolution, exclusion check, and enrichment, then push
channel-ready files out. See `/Users/nac/.claude/plans/mighty-inventing-meadow.md` for the
full design.

## Run it

```bash
cd abm-wrapper
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000

Reads Apollo/HubSpot/HeyReach credentials from the repo-root `.env` (one level up).

## Status

Phase 1 (steps 1-4) is implemented, plus a full UX revision on top of it:

- Step 1 shows the entire normalized CSV in a scrollable table (not a preview), with
  normalization flags visible.
- Domain resolution: local SQLite cache (`data/domain_cache.db`, committed to git — just
  public company/domain facts) checked first, then free Clearbit Autocomplete, then
  optionally Claude + grounded web search (opt-in, small per-lookup cost, needs
  `ANTHROPIC_API_KEY`).
- Exclusion check: an optional pre-filter lets you exclude by job title (e.g. Intern,
  Student) before the HubSpot DNU check runs; both OK and Excluded tracks render live,
  side by side, as full tables. Every exclusion (title-filter, DNU match, or personal-email
  policy) is persisted to `data/domain_cache.db`'s `excluded_leads` table — committed to
  git per an explicit, informed decision to override this repo's usual PII-handling
  convention (unlike the HubSpot exclusion cache, which stays gitignored).
- People Discovery: explicit opt-in gate, a work-email-vs-personal-email policy question,
  and real dropdowns for management level (Apollo's documented `person_seniorities` enum)
  and employee-size buckets. Regions and titles stay editable text fields seeded with
  curated defaults — Apollo has no enumerable list for either (confirmed against their
  docs), so a closed dropdown isn't possible for those two.
- A per-run activity log (sidebar) shows what ran and how long it took.

Steps 5-9 are also implemented:

- Step 5 (Email Reveal): opt-in, shows the row count needing a reveal before running (real
  Apollo credits — 1 per person found, 0 if not). Uses `people/match` with
  `reveal_personal_emails: true`.
- Step 6 (Mobile Phone): opt-in, unchecked by default every run regardless of prior steps.
  Apollo delivers phone numbers asynchronously via webhook, which needs a public URL this
  app doesn't have yet — the step degrades gracefully (0 credits spent, clear note in the
  UI) until it's hosted somewhere with `ABM_WRAPPER_PUBLIC_URL` set.
- Step 7 (Output Files & Name): builds the campaign name from the standard
  `PRIORITY_TEAM_USECASE_REGION_CHANNEL_POCNAME_STARTDATE` convention, splits rows into
  email/LinkedIn/calling files, and pushes the LinkedIn file live to HeyReach as a new list
  — shown with exact list name + lead count and requires explicit confirmation first.
- Step 8 (Associations): read-only pickers for Project (`0-970`), Partner
  (`p6512810_partners`), Event (`p6512810_events`), or skip entirely.
- Step 9 (Preview & Upload): two independent HubSpot pushes (OK track + FARMING-tagged
  excluded-with-email track), each previewed (exact contact count + campaign/list name)
  and requiring its own explicit confirmation before the real write.

**Verified against real accounts (2026-08-14):** an 8-company sample (Vercel, Linear,
Retool, WorkOS, Webflow, Ramp, The Browser Company, Muse) ran through Steps 1-8 end to end
against live Apollo, HubSpot DNU cache, and HubSpot schema APIs — domain resolution, DNU
exclusion (4 of 8 correctly excluded as existing contacts), people discovery, real email
reveal (3/3 verified emails, real credits spent), phone reveal's graceful degrade path
(both opt-in and skip), campaign naming, and the Associations pickers (100 real
projects/partners/events each) all behaved correctly. The final HubSpot write (Step 9) and
HeyReach push (Step 7) were intentionally not executed against the live portal with test
data — those two steps are otherwise fully wired and ready, gated on the same explicit
per-call confirmation as everything else in this app.

Domain resolution's waterfall now has a third fallback: local cache → Clearbit (free) →
Claude + grounded web search (opt-in, needs `ANTHROPIC_API_KEY`) → Apollo org search
(opt-in, costs 1 Apollo credit/company, the priciest step so it's last). Each paid stage is
a separate follow-up button that only appears once the cheaper stage ahead of it has been
tried and something's still unresolved.

**Step 10 (Copy Agent)** — added after reviewing a screen recording of the original
"Xoxoday ABM Wrapper" tool, which has this exact step ("Segment leads, generate email &
LinkedIn copy") and degrades to a clean skip when `ANTHROPIC_API_KEY` isn't set. Ours
matches that behavior and, since a key is now configured, actually generates real copy:
segments the OK-track leads by persona using this repo's own `scripts/icp_titles.py`
taxonomy (60 canonical ICP families mapped to Empuls/Loyalife/Plum and buyer/champion/
influencer roles), then calls Claude Haiku per segment (top 8 by lead count, smaller ones
disclosed as dropped rather than silently skipped) to generate a 2-step email sequence plus
a LinkedIn connection note and follow-up DM. Every generated message uses `{{First Name}}`/
`{{Company}}`/`{{Job Title}}` as literal merge tags, is signed with the run's plain POC name
(not a merge tag, per this project's own sender-name convention), and never uses an em or en
dash, per standing writing-style feedback for this project. Output renders per-segment in
the UI and downloads as a Markdown report (`GET /steps/copy-agent/download`).

**Fixed 2026-08-18: real 500 crash on Excel upload.** Step 1 only ever parsed CSV; uploading
a real `.xlsx` file (which the reference tool's UI explicitly supports — "Data file / sheet")
crashed with `_csv.Error: line contains NUL`, a 500. Step 1 now detects `.xlsx`/`.xlsm` by
filename and parses it properly via `openpyxl`; a genuinely unparseable file (wrong content
for its extension, corrupt, etc.) now returns a clear 400 with the actual reason instead of
crashing.

**Two other fixes from that same recording review:**
- HeyReach failures (`create_list` / `add_leads_batch`) now surface the actual HTTP error
  text instead of a generic message — the reference tool hit a real `400 Client Error` on
  `CreateEmptyList` once, and its own UI showed the raw reason; ours previously would have
  shown only "could not create HeyReach list."
- Confirmed live (not assumed) that Apollo's `reveal_phone_number` hard-requires a real
  `webhook_url` — got the exact `400` back testing it directly. The reference tool's phone
  reveal works because it's genuinely hosted behind a public Cloudflare Tunnel; Step 6's
  "needs public hosting" design here was correct, not a bug to fix.
