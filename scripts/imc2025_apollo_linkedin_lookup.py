"""
One-off: free Apollo bulk_match lookup (by email) to fill in LinkedIn URLs
for the IMC 2025 exhibitor directory extract. Zero credit cost - matches
against Apollo's CRM-synced contacts only, no People Match spend.
"""
import os
import time
import requests
from dotenv import load_dotenv
from _lazy import pd

load_dotenv()
API_KEY = os.environ.get("APOLLO_API_KEY")
BASE = "https://api.apollo.io/v1"
HEADERS = {"Content-Type": "application/json", "Cache-Control": "no-cache"}

IN_CSV = "outputs/imc-2025-directory/imc_2025_exhibitor_emails.csv"
OUT_CSV = "outputs/imc-2025-directory/imc_2025_exhibitor_emails_enriched.csv"
BATCH_SIZE = 10

df = pd.read_csv(IN_CSV)
print(f"Loaded {len(df)} leads")

linkedin_by_email = {}
found = 0

for start in range(0, len(df), BATCH_SIZE):
    batch = df.iloc[start:start + BATCH_SIZE]
    details = [{"email": str(row["email"]).strip()} for _, row in batch.iterrows()]

    retries = 0
    while retries < 3:
        resp = requests.post(
            f"{BASE}/people/bulk_match",
            headers=HEADERS,
            json={"api_key": API_KEY, "details": details, "reveal_personal_emails": False},
            timeout=30,
        )
        if resp.status_code == 429:
            retries += 1
            wait = 30 * retries
            print(f"  rate limited, sleeping {wait}s")
            time.sleep(wait)
            continue
        if resp.status_code != 200:
            print(f"  HTTP {resp.status_code}: {resp.text[:200]}")
            break

        data = resp.json()
        matches = data.get("matches", [])
        for idx, match in enumerate(matches):
            email = details[idx]["email"]
            if match and match.get("linkedin_url"):
                linkedin_by_email[email] = match["linkedin_url"]
                found += 1
        break

    if (start // BATCH_SIZE) % 10 == 0:
        print(f"  [{start + len(batch)}/{len(df)}] found so far: {found}")
    time.sleep(1)

df["linkedin_url"] = df["email"].map(lambda e: linkedin_by_email.get(str(e).strip(), ""))
df.to_csv(OUT_CSV, index=False)
print(f"\nDone. LinkedIn URL found for {found}/{len(df)} ({found/len(df)*100:.1f}%)")
print(f"Saved {OUT_CSV}")
