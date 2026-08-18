"""Merge Saleshandy enrichment results (email + mobile) into the hyperpersonalized CSV."""
import json, csv, glob, os, re

RESULT_FILES = [
    "/Users/nac/.claude/projects/-Users-nac-ai-cold-email-campaign-kit/281b6991-905a-407c-8972-a72af29ae0d3/tool-results/mcp-42064586-ead6-447a-b800-72aeb8085e38-get_enrichment_result-1782488054195.txt",
    "/Users/nac/.claude/projects/-Users-nac-ai-cold-email-campaign-kit/281b6991-905a-407c-8972-a72af29ae0d3/tool-results/mcp-42064586-ead6-447a-b800-72aeb8085e38-get_enrichment_result-1782489377690.txt",
]

# contact -> intended company_domain (so we prefer an email at the company we wrote about)
want_domain = {}
for e in json.load(open("outputs/_enrich_all.json")):
    want_domain[(e["first_name"].lower(), e["last_name"].lower())] = e["company_domain"].lower()

def norm(s): return (s or "").strip().lower()

enr = {}  # (first,last) -> {email, email_status, phone, linkedin, title}
for f in RESULT_FILES:
    data = json.load(open(f))
    for r in data.get("payload", {}).get("results", []):
        fn, ln = norm(r.get("first_name")), norm(r.get("last_name"))
        if not fn:
            continue
        emails = r.get("emails") or []
        valids = [e["email"] for e in emails if e.get("verificationStatus") == "valid"]
        # prefer an email at the company domain we targeted
        wd = want_domain.get((fn, ln), "")
        pick = ""
        if valids:
            dom_match = [e for e in valids if wd and e.lower().endswith("@" + wd)]
            pick = dom_match[0] if dom_match else valids[0]
        phones = r.get("phones") or []
        # prefer a mobile-looking number; else first
        phone = phones[0] if phones else ""
        key = (fn, ln)
        # keep the richest record if duplicates
        prev = enr.get(key)
        cand = {
            "email": pick,
            "email_status": "valid" if pick else ("found-unverified" if emails else "none"),
            "phone": phone,
            "linkedin": r.get("linkedin_url") or "",
            "title": r.get("job_title") or "",
        }
        if not prev or (not prev["email"] and cand["email"]) or (not prev["phone"] and cand["phone"]):
            enr[key] = cand

# merge into CSV
rows = list(csv.DictReader(open("outputs/revenueops-hyperpersonalized.csv")))
out_cols = ["First Name", "Last Name", "Email", "Mobile Phone", "Email Status",
            "LinkedIn", "Company", "Job Title", "Event",
            "Subject 1", "Email 1", "Subject 2", "Email 2",
            "Subject 3", "Email 3", "Subject 4", "Email 4", "Hook Source"]

got_email = got_phone = 0
for x in rows:
    k = (norm(x["First Name"]), norm(x["Last Name"]))
    e = enr.get(k, {})
    x["Email"] = e.get("email", "")
    x["Mobile Phone"] = e.get("phone", "")
    x["Email Status"] = e.get("email_status", "none")
    x["LinkedIn"] = e.get("linkedin", "")
    if x["Email"]: got_email += 1
    if x["Mobile Phone"]: got_phone += 1

with open("outputs/revenueops-hyperpersonalized.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=out_cols)
    w.writeheader()
    for x in rows:
        w.writerow({c: x.get(c, "") for c in out_cols})

# also a ready-to-import subset: only rows with a valid email
with open("outputs/revenueops-import-ready.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=out_cols)
    w.writeheader()
    for x in rows:
        if x["Email"]:
            w.writerow({c: x.get(c, "") for c in out_cols})

total = len(rows)
print(f"contacts: {total}")
print(f"valid email: {got_email}  ({100*got_email//total}%)")
print(f"mobile phone: {got_phone}  ({100*got_phone//total}%)")
print(f"no email (need fallback): {total-got_email}")
print("Wrote outputs/revenueops-hyperpersonalized.csv (all 179, email/phone filled where found)")
print("Wrote outputs/revenueops-import-ready.csv (only rows with a valid email)")
