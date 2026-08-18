from .. import skills_bridge

# normalize.py's detect_columns has no "domain"/"website" role (it's a
# csv-normalizer concept, not this app's) -- detect that column ourselves.
_DOMAIN_HEADER_NAMES = {"domain", "website", "company website", "company domain", "website url"}


def _find_header(headers, names):
    for h in headers:
        if h.strip().lower() in names:
            return h
    return None


def fill_rate(rows, col):
    if not col or not rows:
        return 0.0
    filled = sum(1 for r in rows if (r.get(col) or "").strip())
    return filled / len(rows)


def run(headers, rows, strip_the=False, strip_tagline=False, strip_geo=False):
    out_headers, rows, cols, flags, changed = skills_bridge.normalize_rows(
        headers, rows, strip_the, strip_tagline, strip_geo
    )
    domain_col = _find_header(headers, _DOMAIN_HEADER_NAMES)
    domain_fill_rate = fill_rate(rows, domain_col)
    email_fill_rate = fill_rate(rows, cols.get("email"))

    return {
        "headers": out_headers,
        "rows": rows,
        "detected_columns": cols,
        "flags": flags,
        "changed": changed,
        "row_count": len(rows),
        "domain_fill_rate": domain_fill_rate,
        "email_fill_rate": email_fill_rate,
        "step2_will_skip": domain_fill_rate >= 1.0,
        "step4_will_skip_all": email_fill_rate >= 1.0,
    }
