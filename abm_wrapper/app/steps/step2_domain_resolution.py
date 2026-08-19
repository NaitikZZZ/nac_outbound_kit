import concurrent.futures

from .. import apollo_client

_DOMAIN_HEADER_NAMES = {"domain", "website", "company website", "company domain", "website url"}
_MAX_WORKERS = 10


def _find_header(headers, names):
    for h in headers:
        if h.strip().lower() in names:
            return h
    return None


def run(headers, rows, cols, use_ai_fallback=False, use_apollo_fallback=False):
    """Fills a `Resolved Domain` column for rows missing Domain/Website.
    Waterfall: local cache -> Clearbit Autocomplete (free) -> Claude + grounded
    web search (opt-in, small per-lookup cost, needs ANTHROPIC_API_KEY) ->
    Apollo org search (opt-in, costs 1 Apollo credit per company -- the most
    expensive step, so it only runs if explicitly requested)."""
    domain_col = _find_header(headers, _DOMAIN_HEADER_NAMES)
    company_col = cols.get("company")

    out_col = "Resolved Domain"
    if out_col not in headers:
        headers = headers + [out_col]

    resolved = 0
    by_source = {"existing": 0, "cache": 0, "clearbit": 0, "claude": 0, "apollo": 0, "unresolved": 0}

    # Rows needing an actual lookup are resolved concurrently -- each is an
    # independent network call (cache hit or not), so for a real list of
    # hundreds of companies this is the difference between ~2 minutes and a
    # few seconds run sequentially one row at a time.
    to_resolve = []
    for i, row in enumerate(rows):
        existing = (row.get(domain_col) or "").strip() if domain_col else ""
        if existing:
            row[out_col] = existing
            by_source["existing"] += 1
            continue

        company = (row.get(company_col) or "").strip() if company_col else ""
        if not company:
            row[out_col] = ""
            by_source["unresolved"] += 1
            continue

        to_resolve.append((i, company))

    def _resolve(item):
        i, company = item
        domain, source = apollo_client.resolve_domain(company, use_ai_fallback, use_apollo_fallback)
        return i, domain, source

    if to_resolve:
        with concurrent.futures.ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
            for i, domain, source in pool.map(_resolve, to_resolve):
                rows[i][out_col] = domain or ""
                if domain:
                    resolved += 1
                    by_source[source] += 1
                else:
                    by_source["unresolved"] += 1

    return {
        "headers": headers,
        "rows": rows,
        "resolved_column": out_col,
        "newly_resolved": resolved,
        "by_source": by_source,
        "used_ai_fallback": use_ai_fallback,
        "used_apollo_fallback": use_apollo_fallback,
        "row_count": len(rows),
    }


def should_skip(headers, rows):
    domain_col = _find_header(headers, _DOMAIN_HEADER_NAMES)
    if not domain_col or not rows:
        return False
    return all((r.get(domain_col) or "").strip() for r in rows)
