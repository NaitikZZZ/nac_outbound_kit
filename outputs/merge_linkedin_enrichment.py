"""Merge the LinkedIn-URL enrichment results into the CSV, matching by the URL we sent."""
import json, csv, re, glob, os

NEW_FILES = [
    "/Users/nac/.claude/projects/-Users-nac-ai-cold-email-campaign-kit/281b6991-905a-407c-8972-a72af29ae0d3/tool-results/mcp-42064586-ead6-447a-b800-72aeb8085e38-get_enrichment_result-1782510990953.txt",
    "/Users/nac/.claude/projects/-Users-nac-ai-cold-email-campaign-kit/281b6991-905a-407c-8972-a72af29ae0d3/tool-results/toolu_01RKAqvc4YonHj3Zz6EtgNU5.json",
]

def norm_url(u):
    if not u: return ""
    u = u.strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    return u.rstrip("/")

# url -> (first,last) CSV identity, from the finder output
url2id = {}
for r in json.load(open("outputs/_li_enrich.json")):
    url2id[norm_url(r["linkedin"])] = (r["first"], r["last"])

def load_results(path):
    raw = open(path).read()
    # file may be the MCP json-wrapper [{"type":"text","text":"{...}"}] or the raw payload
    try:
        data = json.loads(raw)
    except Exception:
        return []
    if isinstance(data, list) and data and isinstance(data[0], dict) and "text" in data[0]:
        data = json.loads(data[0]["text"])
    return data.get("payload", {}).get("results", []) if isinstance(data, dict) else []

updates = {}  # (first,last) -> {email, phone}
for f in NEW_FILES:
    for rec in load_results(f):
        urls = [rec.get("linkedin_url")] + (rec.get("social_link") or [])
        ident = None
        for u in urls:
            ident = url2id.get(norm_url(u))
            if ident: break
        if not ident:
            # fallback: match by name
            ident = (rec.get("first_name", ""), rec.get("last_name", ""))
        emails = rec.get("emails") or []
        valids = [e["email"] for e in emails if e.get("verificationStatus") == "valid"]
        phones = rec.get("phones") or []
        if valids or phones:
            updates[ident] = {
                "email": valids[0] if valids else "",
                "phone": phones[0] if phones else "",
            }

# apply to CSV (only fill blanks)
rows = list(csv.DictReader(open("outputs/revenueops-hyperpersonalized.csv")))
def norm(s): return (s or "").strip().lower()
upd_norm = {(norm(a), norm(b)): v for (a, b), v in updates.items()}

new_email = new_phone = 0
for x in rows:
    k = (norm(x["First Name"]), norm(x["Last Name"]))
    u = upd_norm.get(k)
    if not u:
        continue
    if not x["Email"] and u["email"]:
        x["Email"] = u["email"]; x["Email Status"] = "valid"; new_email += 1
    if not x["Mobile Phone"] and u["phone"]:
        x["Mobile Phone"] = u["phone"]; new_phone += 1

cols = list(rows[0].keys())
with open("outputs/revenueops-hyperpersonalized.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader(); w.writerows(rows)

with open("outputs/revenueops-import-ready.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for x in rows:
        if x["Email"]:
            w.writerow(x)

tot = len(rows)
em = sum(1 for x in rows if x["Email"])
ph = sum(1 for x in rows if x["Mobile Phone"])
either = sum(1 for x in rows if x["Email"] or x["Mobile Phone"])
print(f"LinkedIn pass added: {new_email} emails, {new_phone} phones")
print(f"TOTAL now: email {em}/{tot} ({100*em//tot}%) | phone {ph} | reachable {either} ({100*either//tot}%)")
