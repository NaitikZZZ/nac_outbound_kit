# Example output — `heyreach-campaign-launchpad`

> Illustrative sample with **fictional** data. Shows what the skill reports back after launching a campaign
> and what its performance looks like a week in (from `campaigns get` + `stats overall`).

## Launch summary (printed right after `campaigns start`)

```
Campaign:    Q2 SaaS Founders  (id 48211)
Status:      IN_PROGRESS
Lead list:   Q2 SaaS Founders  (420 leads)
Senders:     2 — Jane R., Mark T.
Schedule:    Mon–Fri 09:00–17:00 America/New_York
Sequence:    Connection request → wait 1d → message → follow-up (4 steps)
Exclusions:  prior-contacted, existing-conversations
Next:        first connection requests go out during the next working-hours window
```

## Progress snapshot — `campaigns get --id 48211` → `progressStats` (after ~1 week)

```
totalUsers:               420
totalUsersPending:         95   (not yet entered the sequence)
totalUsersInProgress:     240   (somewhere in the flow)
totalUsersFinished:        70   (completed the sequence)
totalUsersFailed:          12   (see error codes below)
totalUsersExcluded:         3   (matched an exclusion rule)
```

A healthy ramp: pending is draining into in-progress, failures are low (~3%).

## Performance — `stats overall` for the campaign window

| Metric | Value |
|---|--:|
| Connections sent | 312 |
| Connections accepted | 128 |
| **Acceptance rate** | **41%** |
| Messages started | 150 |
| Message replies | 44 |
| **Reply rate** | **29%** |
| Interested (auto-tagged) | 16 |
| Profile views · post likes | 120 · 60 |
| Unique leads contacted | 305 |

## Reading the 12 failures (`campaigns leads` → error codes)

| Count | Error code | Meaning |
|--:|---|---|
| 7 | `FailedToMatchLeadToLinkedIn_TooManyRetries` | Imported URL didn't resolve to a LinkedIn profile — fix the source URLs |
| 3 | `AlreadyAConnection` | Lead was already a 1st-degree connection — a message-first sequence would have reached them |
| 2 | `TryingToResendConnectionRequestTooSoon` | A prior request was withdrawn <21 days ago |

Takeaway: most failures are list-quality issues (bad URLs, mixed connection degree), not sending problems —
a tighter list + `05-mixed-degree-safe` sequence would lift the success rate.
