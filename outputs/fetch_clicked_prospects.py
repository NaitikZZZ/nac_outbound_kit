import os, csv, json, requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("SALESHANDY_API_KEY")
BASE_URL = "https://open-api.saleshandy.com/v1"
SEQUENCE_ID = "lXwA3m9la8"  # ASPR AI — Intent Signal ITS 2026
OUTPUT_FILE = "outputs/intent_signal_clicked_prospects.csv"

headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}

all_clicked = []
page = 1

while True:
    payload = {
        "sequenceIds": [SEQUENCE_ID],
        "startDate": "2025-01-01",
        "endDate": "2026-05-05",
        "pageNum": page,
        "pageLimit": 100
    }
    resp = requests.post(f"{BASE_URL}/analytics/consolidated-stats", headers=headers, json=payload)
    resp.raise_for_status()
    data = resp.json()["payload"]
    records = data["data"]

    clicked = [r for r in records if int(r.get("Click Count", 0) or 0) > 0]
    all_clicked.extend(clicked)
    print(f"Page {page}: {len(records)} records, {len(clicked)} clicked (running total: {len(all_clicked)})")

    if not data.get("hasMore"):
        break
    page = data.get("nextPageNumber", page + 1)

if not all_clicked:
    print("No clicked prospects found.")
else:
    fieldnames = list(all_clicked[0].keys())
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_clicked)
    print(f"\nSaved {len(all_clicked)} clicked prospects to {OUTPUT_FILE}")
