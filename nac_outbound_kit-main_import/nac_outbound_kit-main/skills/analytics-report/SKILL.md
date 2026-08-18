---
name: heyreach-analytics-report
description: |
  Generate READ-ONLY weekly or monthly performance reports across all HeyReach workspaces in an organization, written to a dated markdown file. Use when the user wants an analytics report, a workspace performance digest, org-wide or agency-wide stats, "how are my campaigns doing", weekly/monthly numbers, or KPIs (acceptance rate, reply rate, interested leads) per workspace and as an org roll-up. Requires an organization / tenant API key. Strictly read-only — it never creates, edits, starts, pauses, or deletes anything. Can be scheduled to run automatically.
allowed-tools:
  - Bash(heyreach workspaces list*)
  - Bash(heyreach stats *)
  - Bash(heyreach campaigns list*)
  - Bash(heyreach campaigns get*)
  - Bash(curl *)
  - Bash(date *)
  - Bash(jq *)
  - Read
  - Write
---

# HeyReach Analytics Report (read-only, org-wide)

From one organization API key, produce a weekly or monthly report: an **org roll-up** plus a **per-workspace
breakdown** with period-over-period trends, written to a dated markdown file.

## Triggers

"weekly/monthly HeyReach report", "workspace analytics", "how are my campaigns doing across workspaces",
"org-wide stats", "agency performance digest", "acceptance/reply rates per workspace", "interested-lead report".

## 🔒 Read-only contract (do not violate)

This skill **only reads**. It is safe to run against a live production org. It issues exactly these calls:

- `heyreach workspaces list` — enumerate workspaces
- `GET .../organizations/api-keys/workspaces/{id}` via `curl` — read each workspace's existing public key
  *(temporary: the `heyreach workspaces api-keys` CLI command is currently broken — see Edge cases)*
- `heyreach stats overall` (and optionally `stats by-campaign`, `campaigns list/get`) — read metrics
- `Write` — only to the local report file

**Never call** (and they're not in `allowed-tools`): `workspaces create-api-key` / `create` / `update` /
`invite-*`, any `campaigns create/start/pause/resume/stop-lead/add-leads/update-*`, any `lists`/`leads` write,
`inbox send-message`, or `webhooks` writes. If a workspace lacks a public key, **skip and flag it — never
create one** (that would be a write).

## Prerequisites

An **organization / tenant API key** (HeyReach → Organization settings). The regular workspace key will not
work for `workspaces *`.

```bash
export HEYREACH_TENANT_KEY=your_org_key_here
```

## Set expectations

Before pulling data, give the user a one-line, plain heads-up:
> "Reading stats across N workspaces (read-only), ~3 calls each — building the <weekly|monthly> report."

## How it works

### 1. Validate the org key + list workspaces
```bash
heyreach workspaces list --api-key "$HEYREACH_TENANT_KEY" --limit 100
```
Each item: `{ workspaceId, workspaceName, seatsLimit, usedSeats }`. Paginate with `--offset` if `totalCount > 100`.

### 2. Pick the window (from the system clock)
- **Weekly:** current = trailing 7 days; previous = the 7 days before that (for trends).
- **Monthly:** current = trailing 30 days; previous = the 30 days before that.
```bash
END=$(date -u +%Y-%m-%dT%H:%M:%SZ);  START=$(date -u -v-7d  +%Y-%m-%dT%H:%M:%SZ)   # weekly current (BSD/macOS date)
PREV_END=$START;                     PREV_START=$(date -u -v-14d +%Y-%m-%dT%H:%M:%SZ)
# monthly: use -v-30d and -v-60d.  GNU/Linux date: use `date -u -d '7 days ago'`.
```

### 3. Per workspace, read its public key (read-only)
The CLI's `workspaces api-keys` is currently broken (returns `{}`), so read the key directly — **GET only**:
```bash
KEY=$(curl -s --max-time 20 -H "X-API-KEY: $HEYREACH_TENANT_KEY" \
  "https://api.heyreach.io/api/public/management/organizations/api-keys/workspaces/$WID" | jq -r '.publicApi // empty')
```
If `KEY` is empty → **skip this workspace and add it to the "Skipped" list** (no key exists; do not create one).

### 4. Pull stats for both windows
```bash
heyreach stats overall --api-key "$KEY" --start-date "$START"      --end-date "$END"      | jq '.overallStats'
heyreach stats overall --api-key "$KEY" --start-date "$PREV_START" --end-date "$PREV_END" | jq '.overallStats'
```
Use `.overallStats` (windowed aggregate). Pace requests (org API limit is 300/min); for very large orgs, batch.

### 5. Aggregate → write the markdown report
Sum/blend across workspaces for the roll-up, compute deltas vs the previous window, and write:
`reports/heyreach-<weekly|monthly>-<YYYY-MM-DD>.md` (see layout below). Tell the user the file path.

## Report layout

```
# HeyReach <Weekly|Monthly> Report — <date range>
Generated <timestamp> · N workspaces covered · M skipped (no API key)

## Org roll-up
| Metric | This period | Prev | Δ |
| Connections sent / accepted / acceptance % | … | … | ▲▼ |
| Messages started / replies / reply % | … | … | ▲▼ |
| Interested (auto-tagged) / total tagged / interested % | … | … | ▲▼ |
| InMails · follows · profile views · post likes · unique leads contacted | … | … | ▲▼ |

## Per workspace
| Workspace | Conn sent | Accept % | Msgs | Reply % | Interested | Δ conn |
| Acme Outbound | 142 | 38% | 96 | 29% | 11 | ▲ |
…

## Notable movers
- biggest +/- swings vs last period

## Skipped (no public API key — generate one in-app to include)
- Globex Demo (10293), Initech Agency (10488), …
```

## Metrics reference (`overallStats` fields)

| Group | Fields |
|---|---|
| Volume | `connectionsSent`, `totalMessageStarted`, `inmailMessagesSent`, `follows`, `profileViews`, `postLikes`, `uniqueLeadsContacted` |
| Rates | `connectionAcceptanceRate`, `messageReplyRate`, `inMailReplyRate` (0–1 fractions → ×100 for %) |
| Outcomes | `connectionsAccepted`, `totalMessageReplies`, `totalAutoTagged` |
| Interested | `autoTaggedInterested`, `autoTaggedInterestedRate` |

Use the API's `overallStats.*Rate` values directly — don't recompute from `byDayStats` (per-day acceptance can
exceed 100% because acceptances lag the sends that earned them; the windowed `overallStats` rate is correct).

## Edge cases

- **No public key on a workspace → skip + flag.** Common (many workspaces never had a key generated). Never create one.
- **Zero-activity workspace** → show zeros, don't error.
- **CLI bug — `workspaces api-keys` returns `{}`:** the API returns the keys flat (`{publicApi, n8N, …}`) but the
  CLI expects them nested under `apiKeys`. Use the `curl` GET above until the CLI is fixed; then switch to
  `heyreach workspaces api-keys --workspace-id <id>` and drop `curl` from `allowed-tools`.
- **Rate limit:** org API = 300 req/min; ~3 calls/workspace. Pace for orgs with >100 workspaces.

## Scheduling (optional, set up after the report looks right)

Wrap this in a recurring task (the scheduling skill / cron). Requirements for unattended runs:
- The org key must be in the environment (`HEYREACH_TENANT_KEY`).
- Use **file delivery** (this skill's default) — headless/cron runs may not have MCP connectors (Notion/Slack).
- Recommended cadence: a **weekly** run (e.g. Monday 07:00) and a **monthly** run (1st of month).
