from .. import heyreach_client, skills_bridge


def run(headers, rows, campaign_name):
    """OK track only. Re-normalizes first (idempotent safety net over any
    enrichment-added fields, per the original spec), then splits into three
    channel files by campaign name: email (Smartlead), LinkedIn (HeyReach),
    calling. A row can land in more than one file. The LinkedIn file is
    ALWAYS also pushed live to HeyReach -- this function returns the leads
    payload for that push; main.py calls heyreach_client itself, after the
    user explicitly confirms, since that's the plan's first real external
    write in this phase and needs its own confirmation step."""
    out_headers, norm_rows, cols, _flags, _changed = skills_bridge.normalize_rows(headers, rows)

    prospect_cols = skills_bridge.detect_prospect_columns(out_headers)
    email_col = prospect_cols.get("email")
    linkedin_col = prospect_cols.get("linkedin")
    first_col = cols.get("first_name")
    last_col = cols.get("last_name")

    def has_email(r):
        return bool((r.get("Work Email") or (email_col and r.get(email_col)) or "").strip())

    def has_linkedin(r):
        return bool(linkedin_col and (r.get(linkedin_col) or "").strip())

    def has_phone(r):
        val = (r.get("Mobile Phone") or "").strip()
        return bool(val) and val != "(pending via webhook)"

    email_rows = [r for r in norm_rows if has_email(r)]
    linkedin_rows = [r for r in norm_rows if has_linkedin(r)]
    calling_rows = [r for r in norm_rows if has_phone(r)]

    heyreach_leads = [
        {
            "profileUrl": r.get(linkedin_col, "").strip(),
            "firstName": (r.get(first_col, "") if first_col else "").strip(),
            "lastName": (r.get(last_col, "") if last_col else "").strip(),
        }
        for r in linkedin_rows
    ]

    return {
        "headers": out_headers,
        "rows": norm_rows,
        "campaign_name": campaign_name,
        "email_rows": email_rows,
        "linkedin_rows": linkedin_rows,
        "calling_rows": calling_rows,
        "heyreach_leads": heyreach_leads,
        "counts": {"email": len(email_rows), "linkedin": len(linkedin_rows), "calling": len(calling_rows)},
        "row_count": len(norm_rows),
    }


def push_to_heyreach(campaign_name, heyreach_leads):
    """Actually creates the list and adds leads. Separate from run() so
    main.py can show the user the exact list name + lead count and get
    explicit confirmation before this executes -- the plan's first real
    external write."""
    if not heyreach_leads:
        return {"list_id": None, "added": 0, "failed": 0, "skipped": "no LinkedIn leads to push"}
    list_id, create_error = heyreach_client.create_list(campaign_name)
    if not list_id:
        return {"list_id": None, "added": 0, "failed": len(heyreach_leads), "error": f"could not create HeyReach list: {create_error}"}
    added, failed, push_error = heyreach_client.add_leads_batch(list_id, heyreach_leads)
    result = {"list_id": list_id, "added": added, "failed": failed}
    if push_error:
        result["error"] = f"HeyReach push failed: {push_error}"
    return result
