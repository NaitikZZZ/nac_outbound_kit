"""HeyReach API client -- endpoint shapes confirmed against the sibling
nac_outbound_kit-main_import kit's working script
(scripts/07_heyreach_create_list.py), not guessed.
"""
import time

import requests

from .config import HEYREACH_API_KEY

BASE = "https://api.heyreach.io/api/public"


def _headers():
    return {"X-API-Key": HEYREACH_API_KEY, "Content-Type": "application/json"}


def create_list(name):
    """Returns (list_id, error) -- list_id is None on failure/missing key,
    in which case error holds the actual reason (HTTP status + response
    body) rather than a generic message. Surfacing the real reason matters:
    the reference tool hit a genuine "400 Client Error: Bad Request" here
    once, and a caller can't tell a bad name from a missing key from an
    outage without the actual response text."""
    if not HEYREACH_API_KEY:
        return None, "HEYREACH_API_KEY is not set"
    try:
        resp = requests.post(
            f"{BASE}/list/CreateEmptyList",
            headers=_headers(),
            json={"name": name, "listType": "USER_LIST"},
            timeout=30,
        )
    except Exception as exc:
        return None, f"request failed: {exc}"
    if resp.status_code != 200:
        return None, f"{resp.status_code} {resp.reason}: {resp.text[:300]}"
    return resp.json().get("id"), None


def _post_batch(list_id, batch):
    try:
        resp = requests.post(
            f"{BASE}/list/AddLeadsToListV2",
            headers=_headers(),
            json={"listId": list_id, "leads": batch},
            timeout=60,
        )
    except Exception as exc:
        return 0, len(batch), f"request failed: {exc}"
    if resp.status_code != 200:
        return 0, len(batch), f"{resp.status_code} {resp.reason}: {resp.text[:300]}"
    data = resp.json()
    # A lead already in the list comes back as "updated", not "added" --
    # both mean it's actually in the list, so both count as success here.
    return data.get("addedLeadsCount", 0) + data.get("updatedLeadsCount", 0), data.get("failedLeadsCount", 0), None


def add_leads_batch(list_id, leads):
    """`leads`: list of {"profileUrl", "firstName", "lastName", optionally
    "emailAddress"/"companyName"/"position"}. Batches of 100 per HeyReach's
    documented limit. Returns (added_count, failed_count, last_error) --
    last_error is None unless a batch failed outright, in which case it's
    the real HTTP error text rather than a generic message.

    A freshly created list can take a moment to become writable on
    HeyReach's side -- confirmed live: a batch pushed immediately after
    create_list() came back 100% failed, and resubmitting the identical
    payload seconds later succeeded completely. A whole batch failing (not
    just some leads) is the signature of that race rather than every lead
    being individually bad, so that specific case gets one retry after a
    short delay before being counted as a real failure."""
    if not HEYREACH_API_KEY or not list_id:
        return 0, len(leads), "HEYREACH_API_KEY not set or no list_id"

    total_added, total_failed, last_error = 0, 0, None
    for i in range(0, len(leads), 100):
        batch = leads[i:i + 100]
        added, failed, error = _post_batch(list_id, batch)
        if added == 0 and failed == len(batch):
            time.sleep(5)
            added, failed, error = _post_batch(list_id, batch)
        total_added += added
        total_failed += failed
        if error:
            last_error = error
        if i + 100 < len(leads):
            time.sleep(1)

    return total_added, total_failed, last_error
