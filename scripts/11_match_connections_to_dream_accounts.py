"""
Filter the pulled HeyReach 1st-degree connections (outputs/heyreach_connections/
all_connections.csv) down to people whose company matches one of the dream
accounts in outputs/dream-list-summary-with-LI-verified-2026.csv.

Connections have no LinkedIn company URL (HeyReach doesn't return it for this
endpoint), only a freeform `companyName` scraped from the profile -- so
matching is done by normalized company name, with a domain-root fallback.

Usage:
  python 11_match_connections_to_dream_accounts.py
"""
import csv
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DREAM_LIST = os.path.join(ROOT, "outputs", "dream-list-summary-with-LI-verified-2026.csv")
CONNECTIONS = os.path.join(ROOT, "outputs", "heyreach_connections", "all_connections.csv")
OUT_MATCHED = os.path.join(ROOT, "outputs", "heyreach_connections", "dream_account_connections.csv")
OUT_COMPANY_SUMMARY = os.path.join(ROOT, "outputs", "heyreach_connections", "dream_account_connections_by_company.csv")
OUT_USE_CASE_SUMMARY = os.path.join(ROOT, "outputs", "heyreach_connections", "dream_account_connections_by_use_case.csv")

LEGAL_SUFFIXES = [
    "pvt ltd", "private limited", "ltd", "llc", "inc", "incorporated", "corp",
    "corporation", "co", "limited", "gmbh", "plc", "llp", "lp", "pte",
    "sdn bhd", "bv", "sa", "srl", "ag",
]

# Domain roots that are common English words rather than distinctive brand
# tokens -- confirmed live to produce false matches (e.g. root "self" matched
# "Self-employed", "customer" matched "Customer Success Network", "next"
# matched "Next Generation School"). Excluded from the domain-root fallback
# entirely; exact-name matching still applies to these companies.
GENERIC_DOMAIN_ROOTS = {
    "self", "next", "customer", "momentum", "workforce", "atlantic", "cash",
    "points", "factor", "profit", "alumni", "step", "sage", "blink",
    "madison", "adapt", "enable", "collage", "current", "cult", "base",
    "neon", "momo", "bitcoin", "dialogue", "mesh", "finch", "coins",
    "intellect", "spectrum",
}


def normalize_name(name):
    if not name:
        return ""
    n = name.lower()
    n = re.sub(r"[.,]", " ", n)
    n = re.sub(r"[^a-z0-9 &]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    words = n.split(" ")
    while words and words[-1] in LEGAL_SUFFIXES:
        words.pop()
    # also strip two-word suffixes like "private limited"
    n = " ".join(words)
    for suf in ["private limited", "pvt ltd", "sdn bhd"]:
        if n.endswith(" " + suf):
            n = n[: -len(suf) - 1]
    return n.strip()


def domain_root(domain):
    if not domain or domain == "(No value)":
        return ""
    d = domain.lower().strip()
    d = re.sub(r"^https?://", "", d)
    d = re.sub(r"^www\.", "", d)
    d = d.split("/")[0]
    d = d.split(".")[0]
    return d


def load_dream_accounts():
    with open(DREAM_LIST, newline="") as f:
        rows = list(csv.DictReader(f))

    by_name = {}
    by_domain = {}
    for r in rows:
        norm = normalize_name(r["Company name"])
        r["_norm_name"] = norm
        r["_domain_root"] = domain_root(r["Company Domain Name"])
        if norm and norm not in by_name:
            by_name[norm] = r
        if (
            r["_domain_root"]
            and len(r["_domain_root"]) >= 4
            and r["_domain_root"] not in GENERIC_DOMAIN_ROOTS
            and r["_domain_root"] not in by_domain
        ):
            by_domain[r["_domain_root"]] = r
    return rows, by_name, by_domain


def match_company(conn_company_name, by_name, by_domain):
    norm = normalize_name(conn_company_name)
    if not norm:
        return None, None
    if norm in by_name:
        return by_name[norm], "exact_name"
    # domain-root fallback: domain root appears as a whole word in the
    # normalized connection company name (e.g. "wellpath" in "wellpath inc")
    words = set(norm.split(" "))
    for root, row in by_domain.items():
        if root in words:
            return row, "domain_root"
    return None, None


if __name__ == "__main__":
    dream_rows, by_name, by_domain = load_dream_accounts()
    print(f"Loaded {len(dream_rows)} dream accounts ({len(by_name)} unique normalized names, {len(by_domain)} usable domain roots)")

    matched = []
    company_hits = {}

    with open(CONNECTIONS, newline="") as f:
        reader = csv.DictReader(f)
        total = 0
        for row in reader:
            total += 1
            dream_row, match_type = match_company(row.get("companyName"), by_name, by_domain)
            if not dream_row:
                continue
            key = dream_row["Company name"]
            company_hits.setdefault(key, []).append(row)
            matched.append({
                "dream_company": dream_row["Company name"],
                "domain": dream_row["Company Domain Name"],
                "use_case": dream_row["Use Case"],
                "company_owner": dream_row["Company owner"],
                "match_type": match_type,
                "sender": row.get("sender"),
                "firstName": row.get("firstName"),
                "lastName": row.get("lastName"),
                "position": row.get("position"),
                "location": row.get("location"),
                "profileUrl": row.get("profileUrl"),
                "companyName_raw": row.get("companyName"),
                "connections": row.get("connections"),
                "emailAddress": row.get("emailAddress"),
            })

    print(f"Scanned {total} connections, matched {len(matched)} to {len(company_hits)} dream accounts")

    fieldnames = [
        "dream_company", "domain", "use_case", "company_owner", "match_type",
        "sender", "firstName", "lastName", "position", "location",
        "profileUrl", "companyName_raw", "connections", "emailAddress",
    ]
    with open(OUT_MATCHED, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(matched)
    print(f"Saved: {OUT_MATCHED}")

    with open(OUT_COMPANY_SUMMARY, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["dream_company", "domain", "use_case", "company_owner", "connected_prospect_count", "senders_connected_on"])
        for key, hits in sorted(company_hits.items(), key=lambda kv: -len(kv[1])):
            dream_row = by_name.get(normalize_name(key)) or next(r for r in dream_rows if r["Company name"] == key)
            senders = sorted(set(h.get("sender") for h in hits))
            writer.writerow([key, dream_row["Company Domain Name"], dream_row["Use Case"], dream_row["Company owner"], len(hits), "; ".join(senders)])
    print(f"Saved: {OUT_COMPANY_SUMMARY}")

    by_use_case = {}
    for key, hits in company_hits.items():
        dream_row = by_name.get(normalize_name(key)) or next(r for r in dream_rows if r["Company name"] == key)
        uc = dream_row["Use Case"] or "(blank)"
        bucket = by_use_case.setdefault(uc, {"prospects": 0, "companies": set()})
        bucket["prospects"] += len(hits)
        bucket["companies"].add(key)

    with open(OUT_USE_CASE_SUMMARY, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["use_case", "connected_prospect_count", "dream_account_count", "dream_accounts"])
        for uc, b in sorted(by_use_case.items(), key=lambda kv: -kv[1]["prospects"]):
            writer.writerow([uc, b["prospects"], len(b["companies"]), "; ".join(sorted(b["companies"]))])
    print(f"Saved: {OUT_USE_CASE_SUMMARY}")
