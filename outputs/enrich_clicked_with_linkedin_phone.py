import os, csv, json, time, requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("SALESHANDY_API_KEY")
BASE_URL = "https://open-api.saleshandy.com/v1"
INPUT_FILE = "outputs/intent_signal_clicked_prospects.csv"
OUTPUT_FILE = "outputs/intent_signal_clicked_prospects_enriched.csv"

headers = {"x-api-key": API_KEY}

def get_prospect_fields(email):
    if not email:
        return None, None
    try:
        resp = requests.get(f"{BASE_URL}/prospects", headers=headers,
                            params={"search": email, "pageSize": 1})
        resp.raise_for_status()
    except requests.HTTPError:
        return None, None
    prospects = resp.json().get("payload", [])
    if not prospects:
        return None, None
    attrs = {a["key"]: a["value"] for a in prospects[0].get("attributes", [])}
    linkedin = attrs.get("LinkedIn", "")
    phone = attrs.get("Phone Number", "")
    return linkedin, phone

with open(INPUT_FILE, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    fieldnames = reader.fieldnames + ["LinkedIn URL", "Phone Number"]

cache = {}
enriched = []

for i, row in enumerate(rows):
    email = row.get("Recipient Email", "").strip()
    if email not in cache:
        linkedin, phone = get_prospect_fields(email)
        cache[email] = (linkedin, phone)
        time.sleep(0.15)  # gentle rate limiting
    else:
        linkedin, phone = cache[email]

    row["LinkedIn URL"] = linkedin or ""
    row["Phone Number"] = phone or ""
    enriched.append(row)

    if (i + 1) % 50 == 0:
        print(f"  {i+1}/{len(rows)} done...")

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(enriched)

has_linkedin = sum(1 for r in enriched if r["LinkedIn URL"])
has_phone = sum(1 for r in enriched if r["Phone Number"])
print(f"\nDone. {len(enriched)} rows saved to {OUTPUT_FILE}")
print(f"LinkedIn available: {has_linkedin}/{len(enriched)}")
print(f"Phone available:    {has_phone}/{len(enriched)}")
