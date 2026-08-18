#!/usr/bin/env python3
"""
Build a 1-1 personalized email sequence for the CRO Summit Austin 2026 check-in list.
Peer-note tone, soft ASPR mention (mirrors the SEC Festival NY playbook).

Personalization is GROUNDED in the sheet data only (title, company, industry).
No invented quotes, no fabricated company news. Each {{Personalized Line}} is an
honest, role-anchored peer observation, the same fallback approach used for the
SEC speakers with no public posts.

Outputs:
  outputs/cro-austin-2026-personalized.csv   (Saleshandy import, per-person fields)
"""
import csv, re, os

SRC = "/Users/nac/Documents/ASPR AI/Chief Revenue Officer Summit _ Austin 2026 _ Check In Data.xlsx - Sheet1.csv"
OUT = os.path.join(os.path.dirname(__file__), "cro-austin-2026-personalized.csv")

def clean(s):
    return re.sub(r"\s+", " ", (s or "").strip())

# ---- Role segmentation -------------------------------------------------------
# Each segment gets a Topic, a Personalized Line template, and a Genuine Question.
# {c} = company clause ("at {company}" or "in your seat"), {ind} = industry clause.

def seg_of(title):
    t = title.lower()
    if any(k in t for k in ["revenue operations", "revops", "rev ops", "corporate revops"]):
        return "revops"
    if "enablement" in t:
        return "enablement"
    if "partner" in t:
        return "partnerships"
    if any(k in t for k in ["solution", "solutions engineer", "sales engineer"]):
        return "se"
    if any(k in t for k in ["chief revenue", "cro", "chief sales", "chief commercial",
                             "chief growth", "chief executive", "ceo", "president",
                             "founder", "gtm", "go-to-market"]):
        return "exec"
    if any(k in t for k in ["sales", "vp of sales", "head of sales", "account"]):
        return "sales"
    return "exec"  # default: senior GTM leader

SEG = {
    "exec": {
        "topic": "the gap between the forecast and what the reps can actually run",
        "line": ("The thing I keep chewing on from the revenue seat is how much of the number rides on "
                 "rep execution that never shows up in the CRM {c}. Everyone can see the forecast. "
                 "Almost no one can see whether the motion behind it is actually repeatable."),
        "q":   ("When you look at a soft quarter {c}, how do you tell the difference between a "
                "pipeline problem and an execution problem fast enough to do anything about it? "
                "That diagnosis speed is what I keep getting stuck on."),
    },
    "sales": {
        "topic": "getting reps to run the winning motion consistently, not just the top two",
        "line": ("What stuck with me around the CRO Summit in Austin is how much of a sales team's number "
                 "comes from a handful of reps {c}, while the middle of the roster runs a looser version "
                 "of the same motion. Ramp and coaching time never seems to scale with the headcount."),
        "q":   ("How are you thinking about coaching the middle of the roster {c} without adding "
                "managers? That is the constraint I hear most from sales leaders and I do not think "
                "the usual answers hold up."),
    },
    "revops": {
        "topic": "turning RevOps data into a decision instead of another dashboard",
        "line": ("The RevOps problem I keep circling is that the data {c} is clean enough to report on "
                 "but rarely clean enough to act on in the moment. By the time the dashboard is right, "
                 "the deal or the quarter has already moved."),
        "q":   ("Where is the line for you between RevOps that reports the past and RevOps that changes "
                "what a rep does this week {c}? I keep wondering how much of that gap is tooling versus "
                "how the work is actually structured."),
    },
    "enablement": {
        "topic": "whether enablement actually changes rep behavior in the flow of the deal",
        "line": ("The enablement question I cannot put down is how little of what gets trained {c} "
                 "survives contact with a live deal. The content is good. The moment a rep needs it, "
                 "in the call, is where it tends to fall away."),
        "q":   ("How do you measure whether enablement {c} actually shows up in rep behavior, not just "
                "in completion rates? That gap between trained and applied is the thing I keep poking at."),
    },
    "partnerships": {
        "topic": "making partner-sourced pipeline as predictable as direct",
        "line": ("The partnerships piece I keep thinking about is how partner-sourced pipeline {c} still "
                 "gets managed on relationships and gut, while direct pipeline gets full rigor. The "
                 "motion is different but the accountability bar keeps rising to match."),
        "q":   ("What has actually moved the needle on partner pipeline predictability {c}? Most of what "
                "I hear is still relationship-driven, and I am curious where you have seen real process "
                "beat that."),
    },
    "se": {
        "topic": "capturing the technical judgment that lives only in your best SEs",
        "line": ("The solutions side I find interesting is how much of a technical win {c} rides on "
                 "judgment that lives in a few people's heads and never makes it into a doc. It is the "
                 "hardest knowledge to scale and the easiest to lose."),
        "q":   ("How do you get the tacit stuff your strongest SEs know {c} into a form the rest of the "
                "team can actually use? That capture problem seems unsolved everywhere I look."),
    },
}

def short_company(company):
    # For inline use: drop after-comma descriptors and parentheticals so a clause
    # like "the data at BTC Inc" reads clean (full name stays in the company field).
    c = re.split(r"[,(]", company)[0].strip()
    return c or company

def company_clause(company):
    return f"at {short_company(company)}" if company else "in your seat"

def industry_ok(ind):
    ind = (ind or "").strip().lower()
    return ind and ind != "other"

rows = list(csv.DictReader(open(SRC)))
out = []
seg_counts = {}
for r in rows:
    email = clean(r["Email"])
    if not email:
        continue
    first = clean(r["First Name"])
    last  = clean(r["Last Name"])
    company = clean(r["Company Name"])
    title = clean(r["Job Title"]) or "revenue leader"
    ind = clean(r["Industry"])
    li = clean(r["URL"])
    phone = clean(r["Phone No."])

    seg = seg_of(title)
    seg_counts[seg] = seg_counts.get(seg, 0) + 1
    spec = SEG[seg]
    cc = company_clause(company)

    line = spec["line"].format(c=cc)
    q = spec["q"].format(c=cc)
    # tidy: "in your seat at X" never happens; "at Company" reads clean.
    line = line.replace(" in your seat.", ".").replace(" in your seat,", ",")
    topic = spec["topic"]

    out.append({
        "firstName": first,
        "lastName": last,
        "email": email,
        "phone": phone,
        "company": company,
        "job_title": title,
        "linkedinUrl": li,
        "Topic": topic,
        "Personalized Line": line,
        "Genuine Question": q,
    })

cols = ["firstName","lastName","email","phone","company","job_title",
        "linkedinUrl","Topic","Personalized Line","Genuine Question"]
with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows(out)

# ---- sanity: no dashes anywhere in generated copy ---------------------------
bad = [o for o in out if any(d in (o["Personalized Line"]+o["Genuine Question"]+o["Topic"])
                             for d in ["–","—"," - "])]
print(f"wrote {len(out)} prospects -> {OUT}")
print("segments:", seg_counts)
print("dash violations:", len(bad))
