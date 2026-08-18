from .. import apollo_client, skills_bridge
from ..email_class import classify_email


def should_skip_all(headers, rows, cols):
    email_col = cols.get("email")
    if not email_col or not rows:
        return False
    return all((r.get(email_col) or "").strip() for r in rows)


def run(headers, rows, cols, domain_col, titles=None, employee_ranges=None, locations=None,
        work_email_only=False):
    """OK track only. This step is search-only (0 Apollo credits) -- it finds
    WHO to target, it does not reveal an email. Apollo's api_search response
    gives first_name/last_name_obfuscated/title/has_email, no actual email or
    LinkedIn URL. Actually revealing the email is Step 5's job, not built yet.

    Rows with a work email already: gap-filled, no search needed. Rows with a
    personal email: kept as `Personal Email`, but still searched here to
    identify the right person. If `work_email_only` is set and no work email
    can be confirmed for a personal-email row, that row is EXCLUDED (returned
    separately in `excluded_rows`, not in `rows`) rather than kept on a
    personal address. Rows with no email at all: searched from scratch."""
    titles = titles or skills_bridge.default_people_discovery_titles()
    email_col = cols.get("email")

    out_headers = list(headers)
    for col in ("Work Email", "Personal Email", "Discovered Name", "Discovered Title", "Discovered Has Email"):
        if col not in out_headers:
            out_headers.append(col)
    excluded_headers = out_headers + (["Exclusion Reason"] if "Exclusion Reason" not in out_headers else [])

    kept_rows = []
    excluded_rows = []
    counts = {
        "gap_filled_only": 0, "personal_email_needs_reveal": 0,
        "discovered": 0, "not_found": 0, "excluded_personal_only": 0,
    }

    for row in rows:
        existing_email = (row.get(email_col) or "").strip() if email_col else ""
        email_kind = classify_email(existing_email) if existing_email else "unknown"

        if existing_email and email_kind == "work":
            row["Work Email"] = existing_email
            counts["gap_filled_only"] += 1
            kept_rows.append(row)
            continue

        domain = (row.get(domain_col) or "").strip()
        people = apollo_client.search_people(domain, titles, employee_ranges, locations) if domain else []
        found = bool(people)
        has_confirmed_work_email = found and bool(people[0].get("has_email"))
        if found:
            p = people[0]
            last = p.get("last_name_obfuscated") or p.get("last_name", "")
            row["Discovered Name"] = f"{p.get('first_name', '')} {last}".strip()
            row["Discovered Title"] = p.get("title", "") or ""
            row["Discovered Has Email"] = "yes" if has_confirmed_work_email else "no"
            # Internal only -- not added to out_headers, so it never leaks into
            # CSV output. Step 5 uses this to reveal via Apollo's exact record
            # instead of re-matching on the obfuscated name.
            row["_apollo_person_id"] = p.get("id", "")
            row["_apollo_first_name"] = p.get("first_name", "")

        if existing_email and email_kind == "personal":
            row["Personal Email"] = existing_email
            if work_email_only and not has_confirmed_work_email:
                out_row = dict(row)
                out_row["Exclusion Reason"] = "Personal email only - no work email found"
                excluded_rows.append(out_row)
                counts["excluded_personal_only"] += 1
                continue
            if found:
                counts["personal_email_needs_reveal"] += 1
            kept_rows.append(row)
            continue

        if found:
            counts["discovered"] += 1
        else:
            counts["not_found"] += 1
        kept_rows.append(row)

    return {
        "headers": out_headers,
        "excluded_headers": excluded_headers,
        "rows": kept_rows,
        "excluded_rows": excluded_rows,
        "titles_used": titles,
        "employee_ranges": employee_ranges,
        "locations": locations,
        "work_email_only": work_email_only,
        "counts": counts,
        "row_count": len(kept_rows),
        "note": "Search-only (0 credits) -- actual email reveal happens in Step 5.",
    }
