"""HubSpot client for Associations (read-only) and Preview & Upload (writes).

Read paths (schemas, object 0-970, custom objects) were verified live against
the real portal earlier in this build. The write paths below (contact
upsert, list creation, associations) use HubSpot's standard, well-documented
v3/v4 CRM API shapes but have NOT been exercised against this portal yet --
the plan calls for verifying write scope on the first real run, with the
user's explicit confirmation before it happens.
"""
import requests

from .config import HUBSPOT_API_KEY

BASE = "https://api.hubapi.com"

PROJECT_OBJECT_TYPE = "0-970"
PROJECT_DISPLAY_PROPERTY = "campaign_title"
PARTNER_OBJECT_TYPE = "p6512810_partners"
PARTNER_DISPLAY_PROPERTY = "partner_name"
EVENT_OBJECT_TYPE = "p6512810_events"
EVENT_DISPLAY_PROPERTY = "event_name"


def _headers():
    return {"Authorization": f"Bearer {HUBSPOT_API_KEY}", "Content-Type": "application/json"}


def _list_objects(object_type, display_property, limit=100):
    if not HUBSPOT_API_KEY:
        return []
    try:
        resp = requests.get(
            f"{BASE}/crm/v3/objects/{object_type}",
            headers=_headers(),
            params={"properties": display_property, "limit": limit},
            timeout=20,
        )
    except Exception:
        return []
    if resp.status_code != 200:
        return []
    return [
        {"id": r["id"], "name": r.get("properties", {}).get(display_property) or f"(untitled {r['id']})"}
        for r in resp.json().get("results", [])
    ]


def list_projects():
    return _list_objects(PROJECT_OBJECT_TYPE, PROJECT_DISPLAY_PROPERTY)


def list_partners():
    return _list_objects(PARTNER_OBJECT_TYPE, PARTNER_DISPLAY_PROPERTY)


def list_events():
    return _list_objects(EVENT_OBJECT_TYPE, EVENT_DISPLAY_PROPERTY)


def upsert_contacts(rows, email_key, property_map):
    """`property_map`: {hubspot_property_name: row_key}. Upserts on email.
    Returns list of {"id": contact_id, "email": ..., "new": bool}."""
    if not HUBSPOT_API_KEY or not rows:
        return []
    inputs = []
    for row in rows:
        email = (row.get(email_key) or "").strip()
        if not email:
            continue
        props = {hs_prop: (row.get(row_key) or "").strip() for hs_prop, row_key in property_map.items()}
        props = {k: v for k, v in props.items() if v}
        props["email"] = email
        inputs.append({"idProperty": "email", "id": email, "properties": props})

    results = []
    for i in range(0, len(inputs), 100):
        batch = inputs[i:i + 100]
        try:
            resp = requests.post(
                f"{BASE}/crm/v3/objects/contacts/batch/upsert",
                headers=_headers(),
                json={"inputs": batch},
                timeout=30,
            )
        except Exception:
            continue
        if resp.status_code != 200:
            continue
        for r in resp.json().get("results", []):
            results.append({"id": r["id"], "email": r.get("properties", {}).get("email", ""), "new": r.get("new", False)})
    return results


def create_contact_list(name):
    if not HUBSPOT_API_KEY:
        return None
    try:
        resp = requests.post(
            f"{BASE}/crm/v3/lists",
            headers=_headers(),
            json={"name": name, "objectTypeId": "0-1", "processingType": "MANUAL"},
            timeout=20,
        )
    except Exception:
        return None
    if resp.status_code != 200:
        return None
    return resp.json().get("listId")


def add_list_members(list_id, contact_ids):
    if not HUBSPOT_API_KEY or not list_id or not contact_ids:
        return False
    try:
        resp = requests.put(
            f"{BASE}/crm/v3/lists/{list_id}/memberships/add",
            headers=_headers(),
            json=[str(cid) for cid in contact_ids],
            timeout=30,
        )
    except Exception:
        return False
    return resp.status_code == 200


def associate_contacts(contact_ids, to_object_type, to_object_id):
    """Default association, batch-created, HubSpot's standard v4 shape."""
    if not HUBSPOT_API_KEY or not contact_ids or not to_object_id:
        return False
    inputs = [{"from": {"id": str(cid)}, "to": {"id": str(to_object_id)}} for cid in contact_ids]
    try:
        resp = requests.post(
            f"{BASE}/crm/v4/associations/contacts/{to_object_type}/batch/create/default",
            headers=_headers(),
            json={"inputs": inputs},
            timeout=30,
        )
    except Exception:
        return False
    return resp.status_code in (200, 201)
