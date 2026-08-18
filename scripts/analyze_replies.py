"""Filter HeyReach + Smartlead replies to last week and write a combined report.

Window: Mon 2026-08-03 00:00 UTC through now (covers last calendar week + today,
broken out by date so either reading of "last week" is available).
"""
import csv
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "outputs")

START = datetime(2026, 8, 3, tzinfo=timezone.utc)
CAL_WEEK_END = datetime(2026, 8, 10, tzinfo=timezone.utc)  # Mon..Sun = Aug 3-9


def parse_dt(val):
    if not val:
        return None
    s = str(val).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def load(name):
    p = os.path.join(OUT, name)
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


rows = []

# ------------------------------------------------------------- HeyReach
convos = load("_raw_heyreach_conversations.json")
hr_senders = Counter()
if convos is not None:
    for c in convos:
        prof = c.get("correspondentProfile") or {}
        acct = c.get("linkedInAccount") or {}
        for m in c.get("messages") or []:
            sender = m.get("sender")
            hr_senders[sender] += 1
            if sender == "ME":
                continue
            dt = parse_dt(m.get("createdAt"))
            if not dt or dt < START:
                continue
            rows.append(
                {
                    "platform": "HeyReach",
                    "date": dt.strftime("%Y-%m-%d"),
                    "replied_at": dt.isoformat(),
                    "name": f"{prof.get('firstName','')} {prof.get('lastName','')}".strip(),
                    "contact": prof.get("profileUrl", ""),
                    "title_or_headline": (prof.get("headline") or "")[:120],
                    "company": prof.get("companyName") or "",
                    "campaign_or_sender": acct.get("emailAddress", ""),
                    "category": "",
                    "message": " ".join((m.get("body") or "").split())[:400],
                }
            )
    print(f"[heyreach] {len(convos)} conversations scanned; sender values: {dict(hr_senders)}")
else:
    print("[heyreach] dump missing")

# ------------------------------------------------------------ Smartlead
sl = load("_raw_smartlead_replies.json")
if sl is not None:
    # One lead can reply to several steps; keep the most recent per lead+campaign.
    best = {}
    for r in sl:
        dt = parse_dt(r.get("reply_time"))
        if not dt or dt < START:
            continue
        key = (r.get("_campaign_id"), (r.get("lead_email") or "").lower())
        if key not in best or dt > best[key][0]:
            best[key] = (dt, r)
    for dt, r in best.values():
        rows.append(
            {
                "platform": "Smartlead",
                "date": dt.strftime("%Y-%m-%d"),
                "replied_at": dt.isoformat(),
                "name": r.get("lead_name") or "",
                "contact": r.get("lead_email") or "",
                "title_or_headline": "",
                "company": "",
                "campaign_or_sender": r.get("_campaign_name") or "",
                "category": r.get("lead_category") or "Uncategorized",
                "message": " ".join((r.get("email_subject") or "").split())[:200],
            }
        )
    raw_in_window = sum(1 for r in sl if (parse_dt(r.get("reply_time")) or START.replace(year=1)) >= START)
    print(f"[smartlead] {len(sl)} all-time reply events; {raw_in_window} in window; {len(best)} unique leads")
else:
    print("[smartlead] dump missing (still fetching?)")

rows.sort(key=lambda r: r["replied_at"], reverse=True)

path = os.path.join(OUT, "last-week-replies.csv")
with open(path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["platform"])
    w.writeheader()
    w.writerows(rows)

# ------------------------------------------------------------- summary
print(f"\n{'='*60}\nREPLIES since {START:%Y-%m-%d} -> {len(rows)} total\n{'='*60}")
by_plat = Counter(r["platform"] for r in rows)
cal = [r for r in rows if parse_dt(r["replied_at"]) < CAL_WEEK_END]
print(f"Last calendar week (Aug 3-9): {len(cal)}   |   incl. today (Aug 10): {len(rows)}")
for p, n in by_plat.items():
    print(f"  {p}: {n}")

print("\nBy date:")
for d, n in sorted(Counter(r['date'] for r in rows).items()):
    plats = Counter(r["platform"] for r in rows if r["date"] == d)
    print(f"  {d}  {n:>4}   ({', '.join(f'{k} {v}' for k, v in plats.items())})")

sl_rows = [r for r in rows if r["platform"] == "Smartlead"]
if sl_rows:
    print("\nSmartlead by category:")
    for cat, n in Counter(r["category"] for r in sl_rows).most_common():
        print(f"  {cat}: {n}")
    print("\nTop Smartlead campaigns:")
    for c, n in Counter(r["campaign_or_sender"] for r in sl_rows).most_common(10):
        print(f"  {n:>3}  {c[:70]}")

hr_rows = [r for r in rows if r["platform"] == "HeyReach"]
if hr_rows:
    print("\nHeyReach replies by sending account:")
    for c, n in Counter(r["campaign_or_sender"] for r in hr_rows).most_common(10):
        print(f"  {n:>3}  {c}")

print(f"\nCSV -> {path}")
