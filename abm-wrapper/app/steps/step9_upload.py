from .. import hubspot_client

# Standard HubSpot internal property names -- safe without per-portal
# verification, unlike any custom property would be.
_PROPERTY_MAP_KEYS = ("firstname", "lastname", "company", "jobtitle", "phone")


def _resolve_email(row, cols):
    email_col = cols.get("email")
    return (row.get("Work Email") or row.get("Personal Email") or (email_col and row.get(email_col)) or "").strip()


def _property_map(cols):
    return {
        "firstname": cols.get("first_name") or "Cleaned First Name",
        "lastname": cols.get("last_name") or "Cleaned Last Name",
        "company": cols.get("company") or "Cleaned Company",
        "jobtitle": cols.get("title") or "",
        "phone": "Mobile Phone",
    }


def _rows_with_email(rows, cols):
    out = []
    for row in rows:
        email = _resolve_email(row, cols)
        if email:
            r = dict(row)
            r["_upload_email"] = email
            out.append(r)
    return out


def preview(rows, cols, campaign_name):
    """No writes -- just the count and name to show the user before they
    confirm. Call for both the OK track and the farming track."""
    eligible = _rows_with_email(rows, cols)
    return {"campaign_name": campaign_name, "contact_count": len(eligible)}


def execute(rows, cols, campaign_name, association=None):
    """Real write. `association`: optional {"object_type": ..., "object_id": ...}
    from Step 8's picker. Upserts contacts, creates/fills a list named
    `campaign_name`, associates to the target if given. Returns a summary --
    never raises on partial failure, since a half-done upload with a clear
    report is more recoverable than an exception mid-batch."""
    eligible = _rows_with_email(rows, cols)
    if not eligible:
        return {"campaign_name": campaign_name, "contact_count": 0, "list_id": None, "associated": False, "note": "No rows with an email to upload."}

    upserted = hubspot_client.upsert_contacts(eligible, email_key="_upload_email", property_map=_property_map(cols))
    contact_ids = [r["id"] for r in upserted]

    list_id = hubspot_client.create_contact_list(campaign_name)
    added_to_list = hubspot_client.add_list_members(list_id, contact_ids) if list_id else False

    associated = False
    if association and association.get("object_id") and contact_ids:
        associated = hubspot_client.associate_contacts(contact_ids, association["object_type"], association["object_id"])

    return {
        "campaign_name": campaign_name,
        "contact_count": len(eligible),
        "upserted_count": len(upserted),
        "list_id": list_id,
        "added_to_list": added_to_list,
        "associated": associated,
    }
