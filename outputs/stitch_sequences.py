"""Stitch per-speaker JSON files (outputs/_seq/seq_*.json) into:
  1. revenueops-hyperpersonalized.csv      -> full-body-as-field, Saleshandy UI import
  2. revenueops-hyperpersonalized-preview.md -> readable, grouped by speaker for QA
Email column is left blank on purpose (enrichment is the next step).
"""
import json, glob, csv, os, re

files = sorted(glob.glob("outputs/_seq/seq_*.json"),
               key=lambda p: int(re.search(r"seq_(\d+)", p).group(1)))

written, dropped, broken = [], [], []
for p in files:
    try:
        with open(p) as f:
            rec = json.load(f)
    except Exception as e:
        broken.append((p, str(e)))
        continue
    if rec.get("decision") == "dropped-vendor":
        dropped.append(rec)
    elif rec.get("emails"):
        written.append(rec)
    else:
        broken.append((p, "no emails / unknown decision"))

written.sort(key=lambda r: r.get("name", "").lower())

# ---- CSV (full-body-as-field) ----
csv_path = "outputs/revenueops-hyperpersonalized.csv"
cols = ["First Name", "Last Name", "Email", "Company", "Job Title", "Event",
        "Subject 1", "Email 1", "Subject 2", "Email 2",
        "Subject 3", "Email 3", "Subject 4", "Email 4", "Hook Source"]
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(cols)
    for r in written:
        em = {e["step"]: e for e in r["emails"]}
        def g(step, key):
            return em.get(step, {}).get(key, "")
        w.writerow([
            r.get("firstName", ""), r.get("lastName", ""), "",
            r.get("company", ""), r.get("title", ""), r.get("event", ""),
            g(1, "subject"), g(1, "body"),
            g(2, "subject"), g(2, "body"),
            g(3, "subject"), g(3, "body"),
            g(4, "subject"), g(4, "body"),
            r.get("hookSource", ""),
        ])

# ---- Preview doc ----
md_path = "outputs/revenueops-hyperpersonalized-preview.md"
with open(md_path, "w", encoding="utf-8") as f:
    f.write("# RevOps / CRO Summit Speakers — Hyperpersonalized 4-Step Sequences (ASPR)\n\n")
    f.write(f"{len(written)} speakers. Peer / thought-leadership. 100% full-body-as-field. "
            "No em/en dashes. No signoff (mailbox signature). Cadence Day 1 / 4 / 8 / 12.\n\n")
    f.write("Email column in the CSV is blank pending enrichment.\n\n---\n\n")
    for r in written:
        tag = "" if r.get("dataQuality") == "rich" else "  _(role-based, thin public data)_"
        f.write(f"## {r['name']} - {r.get('title','')}, {r.get('company','')}{tag}\n")
        f.write(f"Event: {r.get('event','')}  \n")
        f.write(f"Hook: {r.get('hookSource','')}\n\n")
        for e in sorted(r["emails"], key=lambda x: x["step"]):
            f.write(f"**E{e['step']} - Day {e['day']} - {e['subject']}**\n\n")
            f.write("> " + e["body"].replace("\n\n", "\n>\n> ").replace("\n", "\n> ") + "\n\n")
        f.write("---\n\n")

print(f"Files parsed: {len(files)}")
print(f"Written sequences: {len(written)}")
print(f"Dropped vendors (in-run): {len(dropped)}")
print(f"Broken/empty: {len(broken)}")
for b in broken[:20]:
    print("  !", b)
print(f"\nWrote {csv_path}")
print(f"Wrote {md_path}")
