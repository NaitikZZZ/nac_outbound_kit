"""Imports the csv-normalizer and hubspot-abm-exclusion skill scripts as modules
(by file path, since they live outside any Python package) and wraps their
pure functions for in-memory use instead of the scripts' CLI/file-I/O paths.

No cleaning/matching logic is reimplemented here -- only the per-row orchestration
glue that main() in each script does inline, adapted to operate on rows already
in memory rather than reading/writing CSV files.
"""
import importlib.util
from collections import Counter
from pathlib import Path

from .config import REPO_ROOT, EXCLUSION_CACHE_PATH


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_normalize = _load_module(
    "csv_normalizer_normalize",
    REPO_ROOT / ".claude" / "skills" / "csv-normalizer" / "scripts" / "normalize.py",
)
_check_exclusions = _load_module(
    "hubspot_abm_exclusion_check",
    REPO_ROOT / ".claude" / "skills" / "hubspot-abm-exclusion" / "scripts" / "check_exclusions.py",
)


def detect_columns(headers):
    return _normalize.detect_columns(headers)


def normalize_rows(headers, rows, strip_the=False, strip_tagline=False, strip_geo=False):
    """Mirrors normalize.py's main() row loop. Mutates and returns `rows` in place,
    plus the output header list, detected columns, flag histogram, and change counts."""
    m = _normalize
    cols = m.detect_columns(headers)
    new_cols = []

    def add_col(name):
        if name not in headers and name not in new_cols:
            new_cols.append(name)
        return name

    has_full = "full_name" in cols
    has_first = "first_name" in cols
    has_last = "last_name" in cols
    if has_full or has_first or has_last:
        add_col("Cleaned Full Name")
        add_col("Cleaned First Name")
        add_col("Cleaned Last Name")
    if "company" in cols:
        add_col("Cleaned Company")
    loc_roles = [r for r in ("city", "state", "country", "location") if r in cols]
    if loc_roles:
        add_col("Cleaned City")
        add_col("Cleaned State")
        add_col("Cleaned State Code")
        add_col("Cleaned Country")
        add_col("Country Code")
    add_col("Normalization Flags")

    flag_counter = Counter()
    changed = Counter()

    for row in rows:
        flags = []

        if has_full or has_first or has_last:
            raw_full = row.get(cols["full_name"], "") if has_full else ""
            raw_first = row.get(cols["first_name"], "") if has_first else ""
            raw_last = row.get(cols["last_name"], "") if has_last else ""

            source = raw_full
            if not source.strip():
                source = " ".join(p for p in (raw_first, raw_last) if p.strip())
            elif has_first and not raw_last.strip() and len(raw_first.split()) > 1:
                flags.append("full_name_in_first_name_column")

            if not raw_full.strip() and has_first and not raw_last.strip() \
                    and len(raw_first.split()) > 1:
                flags.append("full_name_in_first_name_column")

            full_clean, nf = m.clean_person_name(source)
            flags.extend(nf)
            first, last = m.split_name(full_clean)
            if raw_last.strip() and full_clean:
                lc, lf = m.clean_person_name(raw_last)
                if lc and lc.lower() != last.lower() and lc.lower() in full_clean.lower():
                    last = lc
            row["Cleaned Full Name"] = full_clean
            row["Cleaned First Name"] = first
            row["Cleaned Last Name"] = last
            if full_clean and full_clean != m.clean_ws(source):
                changed["name"] += 1

        if "company" in cols:
            raw_co = row.get(cols["company"], "")
            co, cf = m.clean_company(raw_co, strip_the, strip_tagline, strip_geo)
            row["Cleaned Company"] = co
            flags.extend(cf)
            if co and co != m.clean_ws(raw_co):
                changed["company"] += 1

        if loc_roles:
            city = row.get(cols["city"], "") if "city" in cols else ""
            state = row.get(cols["state"], "") if "state" in cols else ""
            country = row.get(cols["country"], "") if "country" in cols else ""
            if "location" in cols and not (city or state):
                pc, ps, pcn, lf = m.parse_location(row.get(cols["location"], ""), known_country=country)
                city, state = pc, ps
                if not country:
                    country = pcn
                flags.extend(lf)

            cn, iso, cf2 = m.canon_country(country, in_country_column=True)
            sn, sc, sf = m.canon_state(state, iso)
            ci, cif = m.canon_city(city)
            if sc and not iso:
                cn, iso = "United States", "US"
                cf2 = cf2 + ["country_inferred_from_state"]
            row["Cleaned City"] = ci
            row["Cleaned State"] = sn
            row["Cleaned State Code"] = sc
            row["Cleaned Country"] = cn
            row["Country Code"] = iso
            flags.extend(cf2 + sf + cif)

        flags = sorted(set(f for f in flags if f))
        for f in flags:
            flag_counter[f.split(":")[0]] += 1
        row["Normalization Flags"] = " | ".join(flags)

    out_headers = list(headers) + [c for c in new_cols if c not in headers]
    return out_headers, rows, cols, dict(flag_counter), dict(changed)


def load_exclusion_cache(cache_path=None):
    path = str(cache_path or EXCLUSION_CACHE_PATH)
    return _check_exclusions.load_cache(path)


def check_exclusions(headers, rows, cache_idx):
    """Mirrors check_exclusions.py's main() row loop. Returns (ok_rows, excluded_rows, cols)."""
    m = _check_exclusions
    cols = m.detect_prospect_columns(headers)
    ok_rows, excluded_rows = [], []
    for row in rows:
        prospect = m.build_prospect_dict(row, cols)
        reasons = m.match_prospect(prospect, cache_idx)
        if reasons:
            out_row = dict(row)
            out_row["Exclusion Reason"] = " | ".join(reasons)
            excluded_rows.append(out_row)
        else:
            ok_rows.append(row)
    return ok_rows, excluded_rows, cols


def detect_prospect_columns(headers):
    """Exposes hubspot-abm-exclusion's column detector (email/company/linkedin/
    name roles) for reuse outside the exclusion step -- e.g. Step 7 needs to
    know which column holds a LinkedIn URL to build the HeyReach file."""
    return _check_exclusions.detect_prospect_columns(headers)


_icp_titles = _load_module("icp_titles_taxonomy", REPO_ROOT / "scripts" / "icp_titles.py")


def default_people_discovery_titles():
    """One representative variant per ICP family from scripts/icp_titles.py,
    as an editable default -- not exhaustive, the caller can override."""
    return [family["variants"][0] for family in _icp_titles.FAMILIES if family.get("variants")]


def icp_families():
    """The full canonical ICP title taxonomy (60 persona families, each with a
    label/product/buyer-role/title variants) -- used by the Copy Agent to
    segment leads by persona before generating tailored copy."""
    return _icp_titles.FAMILIES
