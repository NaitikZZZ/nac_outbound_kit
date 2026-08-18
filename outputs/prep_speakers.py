"""Dedupe the upcoming-event speakers to unique people, split out vendor/sponsor
reps, and emit the keeper list as JSON for the generation run."""
import json, os, re
from build_revops_events import EVENTS

# Companies that SELL software/paid services to sales/revenue/marketing teams.
# Their reps are peers/competitors, not ASPR buyers -> drop per user instruction.
VENDOR_COMPANIES = {
    "clozd", "evergrowth", "outreach", "gong", "hyperbound", "von", "magnify",
    "sifthub", "fullcast", "brevian", "skipl", "actively ai", "ampup", "lative",
    "goodfit", "jumpcrew", "quarrio", "traitware", "11x", "leandata", "creatio",
    "cro collective",  # advisory/consultancy
}

def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())

def split_name(full):
    parts = full.strip().split()
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])

uniq = {}
for ev in EVENTS:
    for name, title, company in ev["speakers"]:
        key = norm(name)
        rec = uniq.setdefault(key, {
            "name": name, "title": title, "company": company, "events": []
        })
        rec["events"].append({
            "event": ev["event"], "date": ev["date"], "location": ev["location"]
        })
        # prefer a non-empty company / most senior-looking title if later dupe has more
        if not rec["company"] and company:
            rec["company"] = company

keepers, vendors = [], []
for rec in uniq.values():
    fn, ln = split_name(rec["name"])
    rec["firstName"], rec["lastName"] = fn, ln
    if norm(rec["company"]) in VENDOR_COMPANIES:
        vendors.append(rec)
    else:
        keepers.append(rec)

# stable order, assign idx
keepers.sort(key=lambda r: r["name"].lower())
for i, r in enumerate(keepers):
    r["idx"] = i

os.makedirs("outputs/_seq", exist_ok=True)
with open("outputs/_speakers_keepers.json", "w") as f:
    json.dump(keepers, f, indent=2)

with open("outputs/revenueops-dropped-vendors.csv", "w") as f:
    f.write("Name,Title,Company,Events\n")
    for r in sorted(vendors, key=lambda x: x["name"].lower()):
        evs = "; ".join(sorted({e["event"] for e in r["events"]}))
        f.write(f'"{r["name"]}","{r["title"]}","{r["company"]}","{evs}"\n')

print(f"Unique speakers: {len(uniq)}")
print(f"Keepers (to generate): {len(keepers)}")
print(f"Dropped vendors: {len(vendors)}")
print("Dropped vendor companies present:",
      sorted({norm(v["company"]) for v in vendors}))
