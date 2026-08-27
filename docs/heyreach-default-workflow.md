# HeyReach Default LinkedIn Workflow

> Extracted from a live, running HeyReach campaign (ID **454732**, "D2C recently Funded - Loyalife - Sanjeeda- SelfTrack - Managers") via `GET /campaign/GetCampaignSequence` on 2026-08-25, at the user's request to make this the standard structure for every future HeyReach campaign built through this kit. **Message copy is not part of the default** - that's always written per campaign. See "Message count" below.

## The structure

The entry point is a `CHECK_IS_CONNECTION` node, not a plain "start with profile visit." Every lead splits into one of two branches immediately:

```
ENTRY: CHECK_IS_CONNECTION
|
|-- Already connected
|     DM1 (wait 3h)
|     |-- replied -> END (1d)
|     `-- no reply -> DM2 (wait 5d)
|          |-- replied -> END (1d)
|          `-- no reply -> DM3 (wait 7d)
|               |-- replied -> END (1d)
|               `-- no reply -> VIEW_PROFILE (wait 1d)
|                    `-- DM4 (wait 3d)
|                         |-- replied -> END (1d)
|                         `-- no reply -> END (wait 15d)
|
`-- Not connected
      VIEW_PROFILE (wait 3h)
      `-- LIKE_POST (wait 3h)
           `-- CONNECTION_REQUEST, no note (wait 1d, withdraw after 30d)
                |-- accepted -> DM1 (wait 1d)
                |     (same DM2/DM3/DM4 chain as the connected branch,
                |      only difference: DM2 waits 6d here instead of 5d)
                `-- not accepted -> END (wait 50d)
```

## Rules encoded in this structure

1. **Connection status gates the entry, it isn't a "skip if connected" campaign setting.** `CHECK_IS_CONNECTION` is the first node in the flowchart itself. Already-connected leads skip straight to DM1. Not-connected leads go profile visit, then like, then connect.
2. **Stop on reply is enforced per message, not just a campaign-level toggle.** Every `MESSAGE` node carries its own `conditionalNode` routing a reply straight to `END` (1 day delay). It's baked into each step, not one global flag.
3. **Four DM messages, not two and not five.** DM1 (intro), DM2 (value prop, wait 5-6d), DM3 (proof/speed point, wait 7d), then a second `VIEW_PROFILE` re-engagement touch (wait 1d) before DM4 (breakup/value-add, wait 3d). Final give-up after DM4 is 15 days.
4. **DM1 has two content variants, one per branch.** Already-connected gets a "since we're connected" opener. Not-connected-then-accepted gets a "thanks for connecting" opener. DM2, DM3, and DM4 content is identical across both branches, only DM1 and the delay before DM2 (5d vs 6d) differ.
5. **Connection requests carry no note** (`messages: [""]`), matching the standing rule against pitch copy on the connect step, and expire after 30 days (`toBeWithdrawnAfterDays: 30`).
6. **If the connection request is never accepted, the lead ends after 50 days.** No further touches beyond that.
7. **Every non-root node needs `actionDelay` >= 3 hours (<= 500 days), including `END` and `LIKE_POST` nodes; `0` is rejected.** Only the true root of the whole tree (`CHECK_IS_CONNECTION` here) may have no delay. The `VIEW_PROFILE` step opening the "not connected" branch is non-root, so it carries the 3h minimum too, not 0h. See `references/node-reference.md` in the sequence-templates skill for the full validation rules, confirmed by live API testing 2026-06-08.
8. **`LIKE_POST` needs a `payload`** (`reactBefore`, `skipDelayIfCannotLike`, `reactionType`/`randomReaction`) - it isn't a no-payload node like `VIEW_PROFILE`/`FOLLOW`.

## Message count is not fixed by this blueprint

The **structure** (branches, delays, stop-on-reply, the second view-profile placement) is the default for every new HeyReach sequence built through this kit. The **number and content of DM messages is always asked of the user** per campaign. Default suggestion is 4 (matching this blueprint), but confirm before building since a given campaign may call for fewer or more.

## Settings observed on the source campaign (reference only, confirm before reusing)

- `excludeContactedFromSenderInOtherCampaign`: true
- `excludeInOtherCampaigns`: false
- `excludeHasOtherAccConversations`: false
- 6 sender accounts rotating

These are campaign-specific choices on the source campaign, not confirmed as universal defaults, flagging for visibility only, not applying automatically.

---

Apply this structure to every new HeyReach sequence built through this kit unless the user asks for a different shape. Superseded sections: the "5 Steps" cadence in `docs/heyreach-api-docs.md` and the HeyReach row in `docs/cadence-blueprint.md`, both updated to point here.
