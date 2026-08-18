import pandas as pd
import requests
import time
import os

API_KEY = os.environ.get("APOLLO_API_KEY", "")
BASE = "https://api.apollo.io/v1"
HEADERS = {"Content-Type": "application/json", "Cache-Control": "no-cache"}

IN_CSV = "outputs/referral-platforms-enrichment/companies.csv"
OUT_CSV = "outputs/referral-platforms-enrichment/apollo_contacts.csv"

TITLE_GROUPS = {
    "product": ["Chief Product Officer", "Head of Product", "VP Product", "VP of Product", "Director of Product"],
    "partnerships": ["Head of Partnerships", "Head of Strategic Partnerships", "VP Partnerships", "VP of Partnerships", "Director of Partnerships", "Strategic Partnerships Manager"],
    "founder": ["Founder", "Co-Founder", "CEO", "Chief Executive Officer"],
}

df = pd.read_csv(IN_CSV)
print(f"Searching {len(df)} companies x {len(TITLE_GROUPS)} title groups (no credit spend, search-only)")

rows = []
for _, r in df.iterrows():
    company, domain = r["company"], r["website"]
    for group, titles in TITLE_GROUPS.items():
        try:
            resp = requests.post(
                f"{BASE}/mixed_people/search",
                headers=HEADERS,
                json={
                    "api_key": API_KEY,
                    "q_organization_domains": domain,
                    "person_titles": titles,
                    "per_page": 5,
                    "page": 1,
                },
                timeout=30,
            )
            if resp.status_code == 429:
                print(f"  rate limited on {company}/{group}, sleeping 30s")
                time.sleep(30)
                continue
            if resp.status_code != 200:
                print(f"  {company}/{group}: HTTP {resp.status_code} - {resp.text[:120]}")
                continue
            people = resp.json().get("people", [])
            for p in people:
                rows.append({
                    "company": company,
                    "domain": domain,
                    "title_group": group,
                    "name": f"{p.get('first_name','')} {p.get('last_name','')}".strip(),
                    "title": p.get("title", ""),
                    "linkedin_url": p.get("linkedin_url", ""),
                    "email": p.get("email", ""),
                    "apollo_id": p.get("id", ""),
                })
        except Exception as e:
            print(f"  {company}/{group}: error {e}")
        time.sleep(1)

out = pd.DataFrame(rows)
out.to_csv(OUT_CSV, index=False)
print(f"Saved {len(out)} contacts -> {OUT_CSV}")
if len(out):
    print(out.groupby(["company", "title_group"]).size().to_string())
