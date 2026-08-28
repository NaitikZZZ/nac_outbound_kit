"""
Push a HeyReach campaign end-to-end onto an existing list, using the kit's
standard flowchart (docs/heyreach-default-workflow.md): CHECK_IS_CONNECTION
entry, already-connected leads skip to DM1, not-connected leads get
visit -> like -> no-note connect -> DM1, then both branches share the same
DM2 -> DM3 -> re-engagement visit -> DM4 chain (DM2's wait is 5d on the
connected branch, 6d on the not-connected branch). Only the message copy
changes per campaign; the shape never does.

Steps:
  1. Create campaign (DRAFT)
  2. Attach sender LinkedIn accounts
  3. Set schedule (timezone-aware)
  4. Attach the lead list + exclusion settings
  5. Push the sequence (fixed shape, your copy)
  6. Leave in DRAFT for review -- this script never calls StartCampaign

Run scripts/07_heyreach_create_list.py first to get a list ID; this script
only builds the campaign around it.

Usage:
  python 17_heyreach_push_campaign.py \\
    --name "P1_EVENTS_PREEVENT_US_LI_naitik16APR26" \\
    --list-id 614694 \\
    --senders 111111,222222 \\
    --copy copy.json

  # Look up sender account IDs first:
  python 17_heyreach_push_campaign.py --list-senders

Required env:
  HEYREACH_API_KEY - your HeyReach API key (from HeyReach Settings > API)

copy.json format (message + fallback required for every slot; fallback
must read naturally on its own, not just the message with the token
removed -- see skills/sequence-templates/references/node-reference.md):
{
  "dm1_connected":     {"message": "Hi {FIRST_NAME}, since we're already connected ...", "fallback": "Hi, since we're already connected ..."},
  "dm1_not_connected":  {"message": "Thanks for connecting, {FIRST_NAME}! ...",            "fallback": "Thanks for connecting! ..."},
  "dm2":                {"message": "...", "fallback": "..."},
  "dm3":                {"message": "...", "fallback": "..."},
  "dm4":                {"message": "...", "fallback": "..."}
}

NOTE on POST /campaign/Create: this kit has never had a confirmed request/
response shape for this endpoint (unlike the others below, which are
documented in docs/heyreach-campaign-api.md). create_campaign() sends the
minimal {"name": ...} body and reads "id" or "campaignId" from the
response. If it errors or returns neither key, the raw response is printed
-- fix create_campaign() against that real response before relying on this
script again, rather than guessing further.
"""
import argparse, json, os, sys, requests

BASE = "https://api.heyreach.io/api/public"

DAY_FIELDS = {
    "mon": "enabledMonday", "tue": "enabledTuesday", "wed": "enabledWednesday",
    "thu": "enabledThursday", "fri": "enabledFriday", "sat": "enabledSaturday", "sun": "enabledSunday",
}


def _headers(api_key):
    return {"X-API-Key": api_key, "Content-Type": "application/json"}


def list_senders(api_key):
    resp = requests.post(f"{BASE}/li_account/GetAll", headers=_headers(api_key), json={}, timeout=30)
    resp.raise_for_status()
    print(json.dumps(resp.json(), indent=2))


def create_campaign(api_key, name):
    resp = requests.post(f"{BASE}/campaign/Create", headers=_headers(api_key), json={"name": name}, timeout=30)
    if resp.status_code != 200:
        sys.exit(f"Create campaign failed: {resp.status_code} - {resp.text[:300]}")
    data = resp.json()
    cid = data.get("id") or data.get("campaignId")
    if not cid:
        sys.exit(f"Create campaign: no id/campaignId in response - {json.dumps(data)[:300]}")
    print(f"Campaign created: {name} (ID: {cid})")
    return cid


def update_accounts(api_key, cid, sender_ids):
    resp = requests.post(
        f"{BASE}/campaign/UpdateAccounts", headers=_headers(api_key),
        json={"campaignId": cid, "linkedInAccountIds": sender_ids}, timeout=30
    )
    print(f"Accounts: {resp.status_code} ({len(sender_ids)} attached)")


def update_schedule(api_key, cid, timezone, start_hour, end_hour, days):
    enabled = {field: False for field in DAY_FIELDS.values()}
    for d in days:
        enabled[DAY_FIELDS[d]] = True
    resp = requests.post(
        f"{BASE}/campaign/UpdateSchedule", headers=_headers(api_key),
        json={
            "campaignId": cid,
            "dailyStartTime": f"{start_hour}:00",
            "dailyEndTime": f"{end_hour}:00",
            "timeZoneId": timezone,
            **enabled,
        }, timeout=15
    )
    print(f"Schedule: {resp.status_code}")


def update_settings(api_key, cid, name, list_id):
    resp = requests.post(
        f"{BASE}/campaign/UpdateSettings", headers=_headers(api_key),
        json={
            "campaignId": cid,
            "name": name,
            "linkedInUserListId": list_id,
            "excludeListId": None,
            "excludeContactedFromOtherCampaigns": False,
            "excludeHasOtherAccConversations": False,
            "excludeContactedFromSenderInOtherCampaign": False,
        }, timeout=15
    )
    print(f"Settings: {resp.status_code}")


def _dm(copy, key, delay, unit, external_ref, conditional, unconditional):
    return {
        "nodeType": "MESSAGE",
        "actionDelay": delay, "actionDelayUnit": unit,
        "payload": {"messages": [copy[key]["message"]], "fallbackMessage": copy[key]["fallback"]},
        "externalReference": external_ref,
        "conditionalNode": conditional,
        "unconditionalNode": unconditional,
    }


def _end(delay, unit="DAY"):
    return {"nodeType": "END", "actionDelay": delay, "actionDelayUnit": unit}


def _dm2_onward(copy, dm2_delay_days):
    dm4 = _dm(copy, "dm4", 3, "DAY", "dm4", _end(1), _end(15))
    view_profile_2 = {
        "nodeType": "VIEW_PROFILE", "actionDelay": 1, "actionDelayUnit": "DAY",
        "externalReference": "view-profile-2", "unconditionalNode": dm4,
    }
    dm3 = _dm(copy, "dm3", 7, "DAY", "dm3", _end(1), view_profile_2)
    return _dm(copy, "dm2", dm2_delay_days, "DAY", "dm2", _end(1), dm3)


def build_sequence(copy):
    connected_branch = _dm(copy, "dm1_connected", 3, "HOUR", "dm1-connected", _end(1), _dm2_onward(copy, 5))

    connection_request = {
        "nodeType": "CONNECTION_REQUEST", "actionDelay": 1, "actionDelayUnit": "DAY",
        "externalReference": "connect",
        "payload": {"messages": [], "toBeWithdrawnAfterDays": 30},
        "conditionalNode": _dm(copy, "dm1_not_connected", 1, "DAY", "dm1-not-connected", _end(1), _dm2_onward(copy, 6)),
        "unconditionalNode": _end(50),
    }
    like_post = {
        "nodeType": "LIKE_POST", "actionDelay": 3, "actionDelayUnit": "HOUR",
        "externalReference": "like-post",
        "payload": {"reactionType": "LIKE", "randomReaction": True, "reactBefore": "MONTH1", "skipDelayIfCannotLike": True},
        "unconditionalNode": connection_request,
    }
    not_connected_branch = {
        "nodeType": "VIEW_PROFILE", "actionDelay": 3, "actionDelayUnit": "HOUR",
        "externalReference": "view-profile-1", "unconditionalNode": like_post,
    }

    return {
        "nodeType": "CHECK_IS_CONNECTION", "actionDelay": 0,
        "externalReference": "entry",
        "conditionalNode": connected_branch,
        "unconditionalNode": not_connected_branch,
    }


def update_sequence(api_key, cid, copy):
    resp = requests.post(
        f"{BASE}/campaign/UpdateSequence", headers=_headers(api_key),
        json={"campaignId": cid, "sequence": build_sequence(copy)}, timeout=30
    )
    if resp.status_code != 200:
        sys.exit(f"Sequence push failed: {resp.status_code} - {resp.text[:500]}")
    print(f"Sequence: {resp.status_code}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--list-senders", action="store_true", help="Print available LinkedIn sender accounts and exit")
    parser.add_argument("--name", help="Campaign name (use naming convention)")
    parser.add_argument("--list-id", type=int, help="HeyReach list ID (from 07_heyreach_create_list.py)")
    parser.add_argument("--senders", help="Comma-separated LinkedIn sender account IDs")
    parser.add_argument("--copy", help="Path to copy JSON file (see module docstring for shape)")
    parser.add_argument("--timezone", default="Asia/Kolkata", help="IANA timezone (default: Asia/Kolkata)")
    parser.add_argument("--start-hour", default="09:00", help="Daily start time HH:MM (default: 09:00)")
    parser.add_argument("--end-hour", default="17:00", help="Daily end time HH:MM (default: 17:00)")
    parser.add_argument("--days", default="mon,tue,wed,thu,fri", help="Comma-separated days (default: mon,tue,wed,thu,fri)")
    args = parser.parse_args()

    api_key = os.environ.get("HEYREACH_API_KEY")
    if not api_key:
        sys.exit("Set HEYREACH_API_KEY env var")

    if args.list_senders:
        list_senders(api_key)
        sys.exit(0)

    missing = [f"--{flag}" for flag, val in
               [("name", args.name), ("list-id", args.list_id), ("senders", args.senders), ("copy", args.copy)]
               if not val]
    if missing:
        sys.exit(f"Missing required args: {', '.join(missing)}")

    with open(args.copy) as f:
        copy = json.load(f)
    required_keys = {"dm1_connected", "dm1_not_connected", "dm2", "dm3", "dm4"}
    missing_keys = required_keys - copy.keys()
    if missing_keys:
        sys.exit(f"copy.json missing keys: {', '.join(sorted(missing_keys))}")

    sender_ids = [int(s.strip()) for s in args.senders.split(",") if s.strip()]
    days = [d.strip().lower() for d in args.days.split(",") if d.strip()]

    cid = create_campaign(api_key, args.name)
    update_accounts(api_key, cid, sender_ids)
    update_schedule(api_key, cid, args.timezone, args.start_hour, args.end_hour, days)
    update_settings(api_key, cid, args.name, args.list_id)
    update_sequence(api_key, cid, copy)

    print()
    print(f"=== DONE ===")
    print(f"Campaign ID: {cid}")
    print(f"Name: {args.name}")
    print(f"List ID: {args.list_id}")
    print(f"Senders: {sender_ids}")
    print(f"Schedule: {args.start_hour}-{args.end_hour} {args.timezone}, {','.join(days)}")
    print(f"Status: DRAFT (review sequence and senders in HeyReach UI, then start manually)")
