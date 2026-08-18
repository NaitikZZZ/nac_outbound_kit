import json
from collections import Counter

from .. import db, skills_bridge
from ..config import EXCLUSION_CACHE_META_PATH

# Titles containing any of these are pre-checked in the Step 3a checklist by
# default -- the team almost always wants these out, but can still uncheck
# a specific one before running the filter.
DEFAULT_EXCLUDE_KEYWORDS = ["intern", "student", "retired"]


def _is_default_excluded(title):
    lowered = title.lower()
    return any(kw in lowered for kw in DEFAULT_EXCLUDE_KEYWORDS)


def cache_age_note():
    if not EXCLUSION_CACHE_META_PATH.exists():
        return None
    meta = json.loads(EXCLUSION_CACHE_META_PATH.read_text(encoding="utf-8"))
    return {"refreshed_at": meta.get("refreshed_at"), "row_count": meta.get("row_count")}


def distinct_titles(headers, rows, cols):
    """Distinct values of the detected title column, with counts, so the user
    can pick some to force-exclude before the DNU check runs (e.g. Intern,
    Student, Former Employee)."""
    title_col = cols.get("title")
    if not title_col:
        return []
    counts = Counter((row.get(title_col) or "").strip() for row in rows)
    counts.pop("", None)
    return [{"title": t, "count": n, "default_excluded": _is_default_excluded(t)} for t, n in counts.most_common()]


def apply_title_exclusion(run_id, headers, rows, cols, excluded_titles):
    """Moves rows whose title matches one of `excluded_titles` out of `rows`.
    Returns (kept_rows, excluded_rows). Runs BEFORE the DNU check -- this and
    the DNU check are two filters feeding the same exclusion track, not two
    separate exclusion concepts."""
    title_col = cols.get("title")
    wanted = {t.strip().lower() for t in excluded_titles if t.strip()}
    if not title_col or not wanted:
        return rows, []

    kept, excluded = [], []
    for row in rows:
        title = (row.get(title_col) or "").strip()
        if title.lower() in wanted:
            out_row = dict(row)
            out_row["Exclusion Reason"] = f"Excluded by title: {title}"
            excluded.append(out_row)
        else:
            kept.append(row)

    if excluded:
        db.record_exclusions(run_id, excluded, source="title_filter")
    return kept, excluded


def run(run_id, headers, rows, run_check):
    """Opt-in per the user's requirement -- pass run_check=False to skip
    entirely and treat every row as OK (no exclusion track). Assumes any
    title-based exclusion has already been applied to `rows` by the caller
    (title filter runs first, DNU check runs on the remainder)."""
    if not run_check:
        return {
            "ran": False,
            "ok_rows": rows,
            "excluded_rows": [],
            "headers": headers,
            "total": len(rows),
            "excluded_count": 0,
            "ok_count": len(rows),
        }

    cache_idx = skills_bridge.load_exclusion_cache()
    ok_rows, excluded_rows, cols = skills_bridge.check_exclusions(headers, rows, cache_idx)
    excluded_headers = headers + (["Exclusion Reason"] if "Exclusion Reason" not in headers else [])

    if excluded_rows:
        db.record_exclusions(run_id, excluded_rows, source="dnu_list")

    return {
        "ran": True,
        "ok_rows": ok_rows,
        "excluded_rows": excluded_rows,
        "headers": headers,
        "excluded_headers": excluded_headers,
        "detected_columns": cols,
        "cache_age": cache_age_note(),
        "total": len(rows),
        "excluded_count": len(excluded_rows),
        "ok_count": len(ok_rows),
    }
