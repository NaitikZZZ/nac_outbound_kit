from .. import apollo_client


def count_needing_reveal(rows):
    """Rows without a Work Email yet but with enough identifying info to try
    a reveal -- used to show the row count (and implied credit cost) to the
    user before they confirm this step, since it spends real Apollo credits."""
    return sum(
        1 for r in rows
        if not (r.get("Work Email") or "").strip()
        and (r.get("_apollo_person_id") or r.get(r.get("_domain_col", ""), ""))
    )


def run(headers, rows, domain_col):
    """OK track only, after Step 4. Real credit spend: 1 credit per person
    Apollo finds an email for (0 if nothing found). Only attempts rows that
    don't already have a Work Email -- rows gap-filled from an existing work
    email in Step 4 are left alone."""
    out_headers = list(headers)
    if "Email Status" not in out_headers:
        out_headers.append("Email Status")

    counts = {"revealed": 0, "already_had_email": 0, "not_found": 0, "skipped_no_identifier": 0}

    for row in rows:
        if (row.get("Work Email") or "").strip():
            counts["already_had_email"] += 1
            continue

        apollo_id = row.get("_apollo_person_id", "")
        first_name = row.get("_apollo_first_name", "")
        domain = (row.get(domain_col) or "").strip() if domain_col else ""

        if not apollo_id and not (first_name and domain):
            counts["skipped_no_identifier"] += 1
            continue

        result = apollo_client.reveal_email(apollo_id=apollo_id, domain=domain, first_name=first_name)
        if result:
            row["Work Email"] = result["email"]
            row["Email Status"] = result["email_status"]
            counts["revealed"] += 1
        else:
            counts["not_found"] += 1

    return {
        "headers": out_headers,
        "rows": rows,
        "counts": counts,
        "row_count": len(rows),
    }
