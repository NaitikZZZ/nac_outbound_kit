#!/usr/bin/env python3
"""Check a prospect CSV against Xoxoday's competitor list.

Matches on company name (exact-normalized, falling back to fuzzy) or
website/email domain. Any single match excludes the row; the reason
column records every rule that fired plus the competitor's category and
threat level so the user can sanity-check.

Usage:
  python3 check_competitors.py --prospects leads.csv \
      --ok-out outputs/leads-ok-to-reach.csv \
      --excluded-out outputs/leads-competitors-excluded.csv \
      --summary-out outputs/leads-competitor-exclusion-summary.md
"""
import argparse
import csv
import difflib
import os
import re
import sys
from collections import defaultdict
from urllib.parse import urlparse

FUZZY_CUTOFF = 0.88

LEGAL_SUFFIXES = [
    "pvt ltd", "private limited", "pvt. ltd.", "llc", "l.l.c.", "inc", "inc.",
    "incorporated", "ltd", "ltd.", "limited", "corp", "corp.", "corporation",
    "co", "co.", "company", "group", "gmbh", "plc", "llp", "s.a.", "sa",
    "b.v.", "bv",
]

COMPETITOR_COLUMN_CANDIDATES = {
    "name": ["name", "company", "company name"],
    "website": ["website", "domain", "url"],
}

PROSPECT_COLUMN_CANDIDATES = {
    "company": ["company", "company name", "account name", "organization", "employer"],
    "website": ["website", "company website", "company domain", "domain"],
    "email": ["email", "email address", "work email", "e-mail", "e mail"],
}


def normalize_whitespace(s):
    return re.sub(r"\s+", " ", (s or "").strip())


def normalize_company(s):
    s = normalize_whitespace(s).lower()
    if not s:
        return ""
    s = re.sub(r"[.,\-&()]", " ", s)
    s = normalize_whitespace(s)
    words = s.split(" ")
    for suffix in sorted(LEGAL_SUFFIXES, key=len, reverse=True):
        suffix_words = suffix.replace(".", "").split(" ")
        n = len(suffix_words)
        if len(words) > n and words[-n:] == suffix_words:
            words = words[:-n]
            break
    return normalize_whitespace(" ".join(words))


def normalize_domain(s):
    s = normalize_whitespace(s).lower()
    if not s:
        return ""
    if "@" in s and "//" not in s:
        # looks like an email address, not a URL
        s = s.split("@")[-1]
    if "://" not in s:
        s = "//" + s
    netloc = urlparse(s).netloc or urlparse(s).path
    netloc = netloc.split("/")[0].split(":")[0]
    netloc = re.sub(r"^www\.", "", netloc)
    return netloc


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


def detect_columns(fieldnames, candidate_map):
    cols = {}
    used = set()
    for key, candidates in candidate_map.items():
        remaining = [fn for fn in fieldnames if fn not in used]
        col = get_column(remaining, candidates)
        cols[key] = col
        if col:
            used.add(col)
    return cols


def load_competitors(path):
    # source file has stray non-UTF-8 bytes in unrelated columns (currency
    # symbols in Revenue/Funding); replace rather than crash since only
    # Name/Website are used for matching.
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    cols = detect_columns(fieldnames, COMPETITOR_COLUMN_CANDIDATES)
    if not cols.get("name"):
        print("ERROR: could not detect a Name column in the competitor CSV.", file=sys.stderr)
        sys.exit(1)

    by_company_exact = defaultdict(list)
    unique_company_buckets = defaultdict(set)
    by_domain = {}

    for row in rows:
        name = row.get(cols["name"], "")
        company_norm = normalize_company(name)
        if company_norm:
            by_company_exact[company_norm].append(row)
            unique_company_buckets[company_norm[:2]].add(company_norm)

        if cols.get("website"):
            domain_norm = normalize_domain(row.get(cols["website"], ""))
            if domain_norm and domain_norm not in by_domain:
                by_domain[domain_norm] = row

    return {
        "by_company_exact": by_company_exact,
        "unique_company_buckets": {k: sorted(v) for k, v in unique_company_buckets.items()},
        "by_domain": by_domain,
    }


def describe_competitor_row(row):
    name = row.get("Name") or row.get("name") or "(unnamed)"
    threat = row.get("Threat") or row.get("threat")
    category = row.get("Category") or row.get("category")
    bits = [b for b in [category, f"{threat} threat" if threat else None] if b]
    return f"{name}" + (f" ({', '.join(bits)})" if bits else "")


def match_prospect(prospect, idx):
    reasons = []

    domain_norm = normalize_domain(prospect.get("website", "")) or normalize_domain(prospect.get("email", ""))
    if domain_norm and domain_norm in idx["by_domain"]:
        row = idx["by_domain"][domain_norm]
        reasons.append(f"Domain match ({domain_norm}) -> competitor {describe_competitor_row(row)}")

    company_norm = normalize_company(prospect.get("company", ""))
    if company_norm:
        if company_norm in idx["by_company_exact"]:
            rows = idx["by_company_exact"][company_norm]
            reasons.append(
                f"Company match (exact after normalization): '{prospect.get('company', '')}' "
                f"-> competitor {describe_competitor_row(rows[0])}"
            )
        else:
            bucket = idx["unique_company_buckets"].get(company_norm[:2], [])
            close = difflib.get_close_matches(company_norm, bucket, n=1, cutoff=FUZZY_CUTOFF)
            if close:
                score = difflib.SequenceMatcher(None, company_norm, close[0]).ratio()
                rows = idx["by_company_exact"][close[0]]
                reasons.append(
                    f"Company match (fuzzy, {score:.0%} similar): '{prospect.get('company', '')}' "
                    f"~ competitor {describe_competitor_row(rows[0])}"
                )

    return reasons


def build_prospect_dict(row, cols):
    return {
        "company": row.get(cols["company"], "") if cols.get("company") else "",
        "website": row.get(cols["website"], "") if cols.get("website") else "",
        "email": row.get(cols["email"], "") if cols.get("email") else "",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prospects", required=True, help="Prospect/lead CSV to check")
    parser.add_argument(
        "--competitors",
        default=os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))),
            "reference", "xoxoday-competitors.csv",
        ),
        help="Path to the competitor list CSV (default: reference/xoxoday-competitors.csv)",
    )
    parser.add_argument("--ok-out", required=True, help="Output CSV for prospects that are NOT competitors")
    parser.add_argument("--excluded-out", required=True, help="Output CSV for excluded (competitor) prospects, with reasons")
    parser.add_argument("--summary-out", required=True, help="Output markdown summary path")
    args = parser.parse_args()

    if not os.path.exists(args.competitors):
        print(f"ERROR: competitor list not found at {args.competitors}.", file=sys.stderr)
        sys.exit(1)

    with open(args.prospects, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        prospect_rows = list(reader)

    cols = detect_columns(fieldnames, PROSPECT_COLUMN_CANDIDATES)
    print("Detected prospect columns:", file=sys.stderr)
    for key, val in cols.items():
        print(f"  {key}: {val or '(not found)'}", file=sys.stderr)
    if not cols.get("company") and not cols.get("website") and not cols.get("email"):
        print(
            "ERROR: could not detect any of company/website/email columns in the prospect CSV. "
            "Check the header names.",
            file=sys.stderr,
        )
        sys.exit(1)

    idx = load_competitors(args.competitors)

    ok_rows = []
    excluded_rows = []
    reason_type_counts = defaultdict(int)
    excluded_companies = defaultdict(int)

    for row in prospect_rows:
        prospect = build_prospect_dict(row, cols)
        reasons = match_prospect(prospect, idx)
        if reasons:
            out_row = dict(row)
            out_row["Competitor Exclusion Reason"] = " | ".join(reasons)
            excluded_rows.append(out_row)
            if prospect.get("company"):
                excluded_companies[prospect["company"]] += 1
            for reason in reasons:
                if reason.startswith("Domain"):
                    reason_type_counts["domain"] += 1
                elif reason.startswith("Company"):
                    reason_type_counts["company"] += 1
        else:
            ok_rows.append(row)

    for path, rows, extra_field in (
        (args.ok_out, ok_rows, None),
        (args.excluded_out, excluded_rows, "Competitor Exclusion Reason"),
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
        "# Competitor Exclusion Summary",
        "",
        f"- Total prospects checked: **{total}**",
        f"- Excluded as competitors: **{excluded_n}**",
        f"- OK to reach out: **{ok_n}**",
        "",
        "## Excluded by match type",
        "",
        f"- Domain match: {reason_type_counts['domain']}",
        f"- Company name match: {reason_type_counts['company']}",
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

    print(f"{total} checked -> {excluded_n} excluded as competitors, {ok_n} OK", file=sys.stderr)
    print(f"OK list: {args.ok_out}", file=sys.stderr)
    print(f"Excluded list: {args.excluded_out}", file=sys.stderr)
    print(f"Summary: {args.summary_out}", file=sys.stderr)


if __name__ == "__main__":
    main()
