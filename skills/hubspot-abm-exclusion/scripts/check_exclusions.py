#!/usr/bin/env python3
"""Check a prospect CSV against the cached HubSpot exclusion list.

Matches on any of: email, LinkedIn URL, company name (fuzzy), or a
first name + last name + company combination. Any single match excludes
the row; the reason column records every rule that fired so it's auditable.

Usage:
  python3 check_exclusions.py --prospects leads.csv \
      --ok-out outputs/leads-ok-to-reach.csv \
      --excluded-out outputs/leads-excluded.csv \
      --summary-out outputs/leads-exclusion-summary.md
"""
import argparse
import csv
import difflib
import json
import os
import re
import sys
from collections import defaultdict

FUZZY_CUTOFF = 0.88

LEGAL_SUFFIXES = [
    "pvt ltd", "private limited", "pvt. ltd.", "llc", "l.l.c.", "inc", "inc.",
    "incorporated", "ltd", "ltd.", "limited", "corp", "corp.", "corporation",
    "co", "co.", "company", "group", "gmbh", "plc", "llp", "s.a.", "sa",
    "b.v.", "bv",
]
STOPWORDS = {
    "the", "and", "of", "a", "an", "inc", "llc", "ltd", "limited", "corp",
    "corporation", "co", "company", "group", "technologies", "technology",
    "tech", "solutions", "services", "gmbh", "plc", "llp",
}

CACHE_LINKEDIN_FIELDS = [
    "hs_linkedin_url", "linkedin_url", "pb_linkedin_profile_url", "linkedin_personal_url",
]

PROSPECT_COLUMN_CANDIDATES = {
    "email": ["email", "email address", "work email", "e-mail", "e mail"],
    "company": ["company", "company name", "account name", "organization", "employer"],
    "linkedin": ["linkedin", "linkedin url", "linkedin profile", "person linkedin url", "linkedin profile url"],
    "first_name": ["first name", "firstname", "first"],
    "last_name": ["last name", "lastname", "last"],
    "full_name": ["full name", "name"],
}


def normalize_whitespace(s):
    return re.sub(r"\s+", " ", (s or "").strip())


def normalize_email(s):
    return normalize_whitespace(s).lower()


def normalize_linkedin(s):
    s = normalize_whitespace(s).lower()
    if not s:
        return ""
    s = re.sub(r"^https?://", "", s)
    s = re.sub(r"^www\.", "", s)
    s = s.split("?")[0]
    s = s.rstrip("/")
    return s


def normalize_company(s):
    s = normalize_whitespace(s).lower()
    if not s:
        return ""
    s = re.sub(r"[.,\-&()]", " ", s)
    s = normalize_whitespace(s)
    words = s.split(" ")
    # strip a trailing legal-suffix word/phrase if present
    for suffix in sorted(LEGAL_SUFFIXES, key=len, reverse=True):
        suffix_words = suffix.replace(".", "").split(" ")
        n = len(suffix_words)
        if len(words) > n and words[-n:] == suffix_words:
            words = words[:-n]
            break
    return normalize_whitespace(" ".join(words))


def company_tokens(s):
    norm = normalize_company(s)
    return {w for w in norm.split(" ") if w and w not in STOPWORDS and len(w) >= 3}


def normalize_name(s):
    return normalize_whitespace(s).lower()


def get_column(fieldnames, candidates):
    lower_map = {fn.lower().strip(): fn for fn in fieldnames}
    for cand in candidates:
        if cand in lower_map:
            return lower_map[cand]
    for cand in candidates:
        for lower_fn, fn in lower_map.items():
            if cand in lower_fn:
                return fn
    return None


def detect_prospect_columns(fieldnames):
    cols = {}
    used = set()
    for key, candidates in PROSPECT_COLUMN_CANDIDATES.items():
        remaining = [fn for fn in fieldnames if fn not in used]
        col = get_column(remaining, candidates)
        cols[key] = col
        if col:
            used.add(col)
    return cols


def load_cache(cache_path):
    with open(cache_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    by_email = {}
    by_linkedin = {}
    by_company_exact = defaultdict(list)
    by_name = defaultdict(list)
    unique_company_buckets = defaultdict(set)

    for row in rows:
        email_norm = normalize_email(row.get("email", ""))
        if email_norm and email_norm not in by_email:
            by_email[email_norm] = row

        for field in CACHE_LINKEDIN_FIELDS:
            li_norm = normalize_linkedin(row.get(field, ""))
            if li_norm and li_norm not in by_linkedin:
                by_linkedin[li_norm] = row

        company_norm = normalize_company(row.get("company", ""))
        if company_norm:
            by_company_exact[company_norm].append(row)
            unique_company_buckets[company_norm[:2]].add(company_norm)

        first_norm = normalize_name(row.get("firstname", ""))
        last_norm = normalize_name(row.get("lastname", ""))
        if first_norm and last_norm:
            by_name[(first_norm, last_norm)].append(row)

    return {
        "by_email": by_email,
        "by_linkedin": by_linkedin,
        "by_company_exact": by_company_exact,
        "unique_company_buckets": {k: sorted(v) for k, v in unique_company_buckets.items()},
        "by_name": by_name,
    }


def describe_cache_row(row):
    name = normalize_whitespace(f"{row.get('firstname', '')} {row.get('lastname', '')}")
    company = row.get("company", "") or "(no company on file)"
    return f"{name or '(no name)'} @ {company}"


def match_prospect(prospect, cache_idx):
    reasons = []

    email_norm = normalize_email(prospect.get("email", ""))
    if email_norm and email_norm in cache_idx["by_email"]:
        row = cache_idx["by_email"][email_norm]
        reasons.append(f"Email match ({email_norm}) -> DNU contact {describe_cache_row(row)}")

    linkedin_norm = normalize_linkedin(prospect.get("linkedin", ""))
    if linkedin_norm and linkedin_norm in cache_idx["by_linkedin"]:
        row = cache_idx["by_linkedin"][linkedin_norm]
        reasons.append(f"LinkedIn URL match -> DNU contact {describe_cache_row(row)}")

    company_norm = normalize_company(prospect.get("company", ""))
    if company_norm:
        if company_norm in cache_idx["by_company_exact"]:
            rows = cache_idx["by_company_exact"][company_norm]
            reasons.append(
                f"Company match (exact after normalization): '{prospect.get('company', '')}' "
                f"-> DNU company '{rows[0].get('company', '')}' ({len(rows)} contact(s) on list)"
            )
        else:
            bucket = cache_idx["unique_company_buckets"].get(company_norm[:2], [])
            close = difflib.get_close_matches(company_norm, bucket, n=1, cutoff=FUZZY_CUTOFF)
            if close:
                score = difflib.SequenceMatcher(None, company_norm, close[0]).ratio()
                rows = cache_idx["by_company_exact"][close[0]]
                reasons.append(
                    f"Company match (fuzzy, {score:.0%} similar): '{prospect.get('company', '')}' "
                    f"~ DNU company '{rows[0].get('company', '')}' ({len(rows)} contact(s) on list)"
                )

    first_norm = normalize_name(prospect.get("first_name", ""))
    last_norm = normalize_name(prospect.get("last_name", ""))
    if first_norm and last_norm and prospect.get("company"):
        candidates = cache_idx["by_name"].get((first_norm, last_norm), [])
        if candidates:
            prospect_tokens = company_tokens(prospect.get("company", ""))
            for row in candidates:
                if prospect_tokens & company_tokens(row.get("company", "")):
                    reasons.append(
                        f"Name + company match: '{prospect.get('first_name','')} {prospect.get('last_name','')}' "
                        f"at '{prospect.get('company','')}' -> DNU contact {describe_cache_row(row)}"
                    )
                    break

    return reasons


def build_prospect_dict(row, cols):
    full_name = row.get(cols.get("full_name") or "", "") if cols.get("full_name") else ""
    first_name = row.get(cols["first_name"], "") if cols.get("first_name") else ""
    last_name = row.get(cols["last_name"], "") if cols.get("last_name") else ""
    if not first_name and not last_name and full_name:
        parts = normalize_whitespace(full_name).split(" ", 1)
        first_name = parts[0] if parts else ""
        last_name = parts[1] if len(parts) > 1 else ""
    return {
        "email": row.get(cols["email"], "") if cols.get("email") else "",
        "company": row.get(cols["company"], "") if cols.get("company") else "",
        "linkedin": row.get(cols["linkedin"], "") if cols.get("linkedin") else "",
        "first_name": first_name,
        "last_name": last_name,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prospects", required=True, help="Prospect/lead CSV to check")
    parser.add_argument(
        "--cache",
        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache", "exclusion_cache.csv"),
        help="Path to the cached exclusion list CSV (default: skill's cache/exclusion_cache.csv)",
    )
    parser.add_argument("--ok-out", required=True, help="Output CSV for prospects OK to reach out")
    parser.add_argument("--excluded-out", required=True, help="Output CSV for excluded prospects, with reasons")
    parser.add_argument("--summary-out", required=True, help="Output markdown summary path")
    args = parser.parse_args()

    if not os.path.exists(args.cache):
        print(
            f"ERROR: cache file not found at {args.cache}. Run refresh_cache.py first "
            "(requires HUBSPOT_API_KEY in .env).",
            file=sys.stderr,
        )
        sys.exit(1)

    meta_path = os.path.join(os.path.dirname(args.cache), "meta.json")
    cache_age_note = ""
    if os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        cache_age_note = f"Cache last refreshed: {meta.get('refreshed_at')} ({meta.get('row_count')} DNU contacts)"

    with open(args.prospects, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        prospect_rows = list(reader)

    cols = detect_prospect_columns(fieldnames)
    print("Detected prospect columns:", file=sys.stderr)
    for key, val in cols.items():
        print(f"  {key}: {val or '(not found)'}", file=sys.stderr)
    if not any([cols.get("email"), cols.get("company"), cols.get("linkedin")]):
        print(
            "ERROR: could not detect any of email/company/linkedin columns in the prospect CSV. "
            "Check the header names.",
            file=sys.stderr,
        )
        sys.exit(1)

    cache_idx = load_cache(args.cache)

    ok_rows = []
    excluded_rows = []
    reason_type_counts = defaultdict(int)
    excluded_companies = defaultdict(int)

    for row in prospect_rows:
        prospect = build_prospect_dict(row, cols)
        reasons = match_prospect(prospect, cache_idx)
        if reasons:
            out_row = dict(row)
            out_row["Exclusion Reason"] = " | ".join(reasons)
            excluded_rows.append(out_row)
            if prospect.get("company"):
                excluded_companies[prospect["company"]] += 1
            for reason in reasons:
                if reason.startswith("Email"):
                    reason_type_counts["email"] += 1
                elif reason.startswith("LinkedIn"):
                    reason_type_counts["linkedin"] += 1
                elif reason.startswith("Company"):
                    reason_type_counts["company"] += 1
                elif reason.startswith("Name"):
                    reason_type_counts["name_plus_company"] += 1
        else:
            ok_rows.append(row)

    for path, rows, extra_field in (
        (args.ok_out, ok_rows, None),
        (args.excluded_out, excluded_rows, "Exclusion Reason"),
    ):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        out_fieldnames = list(fieldnames)
        if extra_field and extra_field not in out_fieldnames:
            out_fieldnames = out_fieldnames + [extra_field]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=out_fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    total = len(prospect_rows)
    excluded_n = len(excluded_rows)
    ok_n = len(ok_rows)

    top_companies = sorted(excluded_companies.items(), key=lambda kv: -kv[1])[:10]

    summary_lines = [
        "# Exclusion Check Summary",
        "",
        cache_age_note,
        "",
        f"- Total prospects checked: **{total}**",
        f"- Excluded: **{excluded_n}**",
        f"- OK to reach out: **{ok_n}**",
        "",
        "## Excluded by match type",
        "",
        f"- Email match: {reason_type_counts['email']}",
        f"- LinkedIn URL match: {reason_type_counts['linkedin']}",
        f"- Company name match: {reason_type_counts['company']}",
        f"- Name + company match: {reason_type_counts['name_plus_company']}",
        "",
    ]
    if top_companies:
        summary_lines.append("## Top excluded companies")
        summary_lines.append("")
        for company, count in top_companies:
            summary_lines.append(f"- {company}: {count}")
        summary_lines.append("")

    os.makedirs(os.path.dirname(args.summary_out) or ".", exist_ok=True)
    with open(args.summary_out, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))

    print(f"{total} checked -> {excluded_n} excluded, {ok_n} OK to reach out", file=sys.stderr)
    print(f"OK list: {args.ok_out}", file=sys.stderr)
    print(f"Excluded list: {args.excluded_out}", file=sys.stderr)
    print(f"Summary: {args.summary_out}", file=sys.stderr)


if __name__ == "__main__":
    main()
