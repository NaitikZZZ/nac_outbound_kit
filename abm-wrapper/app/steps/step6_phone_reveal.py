from .. import apollo_client
from ..config import PUBLIC_BASE_URL


def run(headers, rows, domain_col):
    """OK track only. Explicit opt-in (the caller/UI gates on a separate
    "enrich phones?" checkbox, default off -- this function itself always
    runs when called, the gate lives in main.py per the established pattern).

    Apollo's phone reveal is asynchronous (delivered via webhook, "several
    minutes" later per their docs) -- without PUBLIC_BASE_URL configured
    (this app isn't hosted anywhere public yet), this degrades gracefully:
    no calls are made, no credits spent, and the result says why."""
    out_headers = list(headers)
    if "Mobile Phone" not in out_headers:
        out_headers.append("Mobile Phone")

    if not PUBLIC_BASE_URL:
        return {
            "headers": out_headers,
            "rows": rows,
            "attempted": 0,
            "pending": 0,
            "note": (
                "Phone reveal needs a public URL for Apollo to call back with results "
                "(their API delivers phone numbers async via webhook) -- not available "
                "until this app is hosted. No credits were spent."
            ),
            "row_count": len(rows),
        }

    attempted = 0
    pending = 0
    for row in rows:
        if (row.get("Mobile Phone") or "").strip():
            continue
        apollo_id = row.get("_apollo_person_id", "")
        first_name = row.get("_apollo_first_name", "")
        domain = (row.get(domain_col) or "").strip() if domain_col else ""
        if not apollo_id and not (first_name and domain):
            continue
        attempted += 1
        result = apollo_client.reveal_phone(apollo_id=apollo_id, domain=domain, first_name=first_name)
        if result:
            row["Mobile Phone"] = "(pending via webhook)"
            pending += 1

    return {
        "headers": out_headers,
        "rows": rows,
        "attempted": attempted,
        "pending": pending,
        "note": "Requests sent; Apollo delivers numbers to the webhook receiver asynchronously.",
        "row_count": len(rows),
    }
