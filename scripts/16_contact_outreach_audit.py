"""
Real outreach audit for the events-raw-us-ok-to-reach-enriched CSV.

For every contact with an email, pulls EXACT Smartlead touchpoint data
(not estimated) via:
  GET /leads?email=...                                        -> global lead + campaigns
  GET /campaigns/{campaign_id}/leads/{lead_id}/message-history -> exact SENT/REPLY events

For every contact with a LinkedIn URL, pulls HeyReach touch data via:
  POST /campaign/GetAll                 -> all campaigns (scoped to created-in-2026)
  POST /campaign/GetLeadsFromCampaign   -> per-lead connection/message status, keyed by profileUrl
  POST /inbox/GetConversationsV2        -> actual DM messages + timestamps, keyed by profileUrl

AE ownership via HubSpot batch read (by email, ALL matched contacts -- not sampled):
  POST /crm/v3/objects/contacts/batch/read
  GET  /crm/v3/owners

All touchpoints/replies are filtered to >= 2026-01-01 (the audit window the
user specified). OOO replies are excluded from "responded" via Smartlead's
lead_category_id == 6 ("Out Of Office") and, for HeyReach (which has no
category field), an OOO keyword heuristic on the reply text.

Usage:
    .venv/bin/python3 scripts/16_contact_outreach_audit.py
"""
import csv
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
INPUT_CSV = Path.home() / "Downloads" / "events-raw-us-ok-to-reach-enriched 1.csv"
OUT_DIR = ROOT / "outputs" / "events-us-outreach-audit-2026"
OUT_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT = OUT_DIR / "_checkpoint.json"

CUTOFF = datetime(2026, 1, 1, tzinfo=timezone.utc)

AE_NAMES = {
    "Sarah Payne", "James Formen", "Srinidhi S", "Austin",
    "Shakeeb Husain", "Abhimanyu Choudhary", "Anju Choudhary", "Amy Everman",
}
SDR_NAMES = {"Shameel Khan", "Yash Handa", "Ganesh Rumaal", "Rakesh M"}

OOO_CATEGORY_ID = 6

OOO_KEYWORDS = [
    "out of office", "out-of-office", " ooo ", "ooo until", "ooo,", "ooo.",
    "on leave", "on vacation", "annual leave", "on pto", " pto ",
    "auto-reply", "automatic reply", "automated reply", "currently away",
    "out of the office", "returning on", "back in office", "back on",
    "will be back", "limited access to email", "away from my desk",
]


def load_env():
    env = {}
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


ENV = load_env()
SL_KEY = ENV.get("SMARTLEAD_API_KEY")
HR_KEY = ENV.get("HEYREACH_API_KEY")
HS_KEY = ENV.get("HUBSPOT_API_KEY")

SL_BASE = "https://server.smartlead.ai/api/v1"
HR_BASE = "https://api.heyreach.io/api/public"
HS_BASE = "https://api.hubapi.com"


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def parse_dt(val):
    if not val:
        return None
    s = str(val).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def is_ooo_text(text):
    t = " " + (text or "").lower() + " "
    return any(k in t for k in OOO_KEYWORDS)


def sl_get(path, params, retries=6):
    for attempt in range(retries):
        try:
            r = requests.get(f"{SL_BASE}{path}", params={**params, "api_key": SL_KEY}, timeout=30)
        except requests.exceptions.RequestException:
            time.sleep(min(2 ** attempt, 20))
            continue
        if r.status_code == 200:
            return r.json()
        if r.status_code == 429:
            time.sleep(min(2 ** attempt, 20))
            continue
        if r.status_code >= 500:
            time.sleep(min(2 ** attempt, 15))
            continue
        return None  # 400/404 -> no such lead
    return None


def smartlead_lookup(email):
    """Exact Smartlead touch data for one email, filtered to >= CUTOFF."""
    data = sl_get("/leads", {"email": email})
    if not data or not data.get("id"):
        return {"matched": False}

    lead_id = data["id"]
    campaigns = data.get("lead_campaign_data") or []
    touches = 0
    last_touch = None
    campaign_names = []
    replies = []  # list of (time, ooo_bool, subject)

    for c in campaigns:
        camp_id = c.get("campaign_id")
        if not camp_id:
            continue
        hist = sl_get(f"/campaigns/{camp_id}/leads/{lead_id}/message-history", {})
        if not hist:
            continue
        cat_id = c.get("lead_category_id")
        for ev in hist.get("history", []):
            t = parse_dt(ev.get("time"))
            if not t or t < CUTOFF:
                continue
            etype = (ev.get("type") or "").upper()
            if etype == "SENT":
                touches += 1
                if not last_touch or t > last_touch:
                    last_touch = t
                if c.get("campaign_name") not in campaign_names:
                    campaign_names.append(c.get("campaign_name"))
            elif etype == "REPLY":
                ooo = (cat_id == OOO_CATEGORY_ID) or is_ooo_text(ev.get("email_body"))
                replies.append((t, ooo, (ev.get("subject") or "")[:80]))

    real_replies = [r for r in replies if not r[1]]
    return {
        "matched": True,
        "touches": touches,
        "last_touch": last_touch,
        "campaigns": campaign_names,
        "replied": bool(real_replies),
        "replied_but_ooo_only": bool(replies) and not real_replies,
        "reply_detail": "; ".join(f"{r[0].date()}: {r[2]}" for r in real_replies[:2]),
    }


def run_smartlead(emails):
    results = {}
    done = 0
    with ThreadPoolExecutor(max_workers=16) as ex:
        futs = {ex.submit(smartlead_lookup, e): e for e in emails}
        for fut in as_completed(futs):
            e = futs[fut]
            try:
                results[e] = fut.result()
            except Exception as ex_err:
                results[e] = {"matched": False, "error": str(ex_err)}
            done += 1
            if done % 200 == 0:
                log(f"  Smartlead: {done}/{len(emails)}")
    return results


# --------------------------------------------------------------- HeyReach

def hr_post(path, body, retries=6):
    for attempt in range(retries):
        try:
            r = requests.post(
                f"{HR_BASE}{path}",
                headers={"X-API-Key": HR_KEY, "Content-Type": "application/json"},
                json=body,
                timeout=30,
            )
        except requests.exceptions.RequestException:
            time.sleep(min(2 ** attempt, 20))
            continue
        if r.status_code == 200:
            return r.json()
        if r.status_code == 429:
            time.sleep(min(2 ** attempt, 20))
            continue
        if r.status_code >= 500:
            time.sleep(min(2 ** attempt, 15))
            continue
        return None
    return None


def norm_url(u):
    return (u or "").strip().lower().rstrip("/").replace("https://www.", "https://").replace("http://", "https://")


def heyreach_campaign_status(target_urls):
    """Scan every 2026 HeyReach campaign's leads once; keep only target matches."""
    campaigns = []
    offset = 0
    while True:
        d = hr_post("/campaign/GetAll", {"offset": offset, "limit": 100})
        if not d:
            break
        items = d.get("items", [])
        campaigns.extend(items)
        total = d.get("totalCount", 0)
        offset += 100
        if offset >= total:
            break

    c2026 = [c for c in campaigns if str(c.get("creationTime", "")).startswith("2026")]
    log(f"  HeyReach: scanning {len(c2026)} campaigns created in 2026 (of {len(campaigns)} total)...")

    def scan_one(camp):
        camp_id = camp["id"]
        rows = []
        offset = 0
        while True:
            d = hr_post("/campaign/GetLeadsFromCampaign", {"campaignId": camp_id, "offset": offset, "limit": 100})
            if not d:
                break
            items = d.get("items", [])
            for it in items:
                prof = it.get("linkedInUserProfile") or {}
                purl = norm_url(prof.get("profileUrl") or it.get("profileUrl"))
                if purl in target_urls:
                    rows.append((purl, {
                        "campaign": camp.get("name"),
                        "connection_status": it.get("leadConnectionStatus"),
                        "message_status": it.get("leadMessageStatus"),
                    }))
            total = d.get("totalCount", 0)
            offset += 100
            if offset >= total or not items:
                break
        return rows

    status = {}  # norm_url -> list of {campaign, connection_status, message_status}
    done = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(scan_one, c): c for c in c2026}
        for fut in as_completed(futs):
            for purl, info in fut.result():
                status.setdefault(purl, []).append(info)
            done += 1
            if done % 40 == 0:
                log(f"    campaign {done}/{len(c2026)}...")
    return status


def heyreach_conversations(target_urls):
    convos, offset = [], 0
    while True:
        d = hr_post("/inbox/GetConversationsV2", {"filters": {}, "offset": offset, "limit": 100})
        if not d:
            break
        items = d.get("items", [])
        convos.extend(items)
        total = d.get("totalCount", 0)
        offset += 100
        if offset >= total or not items:
            break

    msgs_by_profile = {}
    for c in convos:
        prof = c.get("correspondentProfile") or {}
        purl = norm_url(prof.get("profileUrl"))
        if purl not in target_urls:
            continue
        for m in c.get("messages") or []:
            t = parse_dt(m.get("createdAt"))
            if not t or t < CUTOFF:
                continue
            msgs_by_profile.setdefault(purl, []).append({
                "sender": m.get("sender"),
                "time": t,
                "body": m.get("body") or "",
            })
    return msgs_by_profile


def build_heyreach_activity(target_urls):
    status = heyreach_campaign_status(target_urls)
    msgs = heyreach_conversations(target_urls)

    activity = {}
    for purl in target_urls:
        st = status.get(purl, [])
        ms = sorted(msgs.get(purl, []), key=lambda m: m["time"])

        connected = any(s["connection_status"] in ("ConnectionSent", "ConnectionAccepted") for s in st)
        me_msgs = [m for m in ms if m["sender"] == "ME"]
        their_msgs = [m for m in ms if m["sender"] != "ME"]

        touches = (1 if connected else 0) + len(me_msgs)
        last_touch = None
        for m in me_msgs:
            if not last_touch or m["time"] > last_touch:
                last_touch = m["time"]

        real_replies = [m for m in their_msgs if not is_ooo_text(m["body"])]
        ooo_only = bool(their_msgs) and not real_replies

        activity[purl] = {
            "matched": bool(st or ms),
            "touches": touches,
            "last_touch": last_touch,
            "campaigns": sorted({s["campaign"] for s in st if s["campaign"]}),
            "replied": bool(real_replies),
            "replied_but_ooo_only": ooo_only,
            "reply_detail": "; ".join(f"{m['time'].date()}: {m['body'][:80]}" for m in real_replies[:2]),
        }
    return activity


# --------------------------------------------------------------- HubSpot

OWNER_FIELDS = ["hubspot_owner_id", "ae_owner", "account_owner", "sdr_owner"]


def hubspot_ae_lookup(emails):
    """Batch-read all matched contacts by email (ALL, not sampled) and resolve
    the assigned owner id to a name via /crm/v3/owners. If that endpoint isn't
    authorized for this API key (missing Owners read scope), returns the raw
    owner id per email instead so the caller can still report "has an owner"
    and flag the ones that need manual name resolution.
    """
    headers = {"Authorization": f"Bearer {HS_KEY}", "Content-Type": "application/json"}

    owners = {}
    owners_scope_ok = True
    after = None
    while True:
        params = {"limit": 100}
        if after:
            params["after"] = after
        r = requests.get(f"{HS_BASE}/crm/v3/owners", headers=headers, params=params, timeout=20)
        if r.status_code == 403:
            owners_scope_ok = False
            log("  HubSpot /owners returned 403 -- API key lacks Owners read scope. "
                "Will report raw owner IDs instead of names.")
            break
        if r.status_code != 200:
            break
        d = r.json()
        for o in d.get("results", []):
            name = f"{o.get('firstName', '')} {o.get('lastName', '')}".strip()
            owners[o["id"]] = name
        paging = d.get("paging", {}).get("next", {})
        after = paging.get("after")
        if not after:
            break

    owner_id_to_ae = {}
    for oid, name in owners.items():
        for ae in AE_NAMES | SDR_NAMES:
            if ae.lower() in name.lower():
                owner_id_to_ae[oid] = name
                break

    email_owner_id = {}
    emails = list(emails)
    for i in range(0, len(emails), 100):
        batch = emails[i:i + 100]
        body = {
            "properties": ["email"] + OWNER_FIELDS,
            "idProperty": "email",
            "inputs": [{"id": e} for e in batch],
        }
        r = requests.post(f"{HS_BASE}/crm/v3/objects/contacts/batch/read", headers=headers, json=body, timeout=30)
        if r.status_code not in (200, 207):
            log(f"  HubSpot batch {i}: HTTP {r.status_code} {r.text[:200]}")
            continue
        for res in r.json().get("results", []):
            props = res.get("properties", {})
            email = (props.get("email") or "").strip().lower()
            oid = next((props.get(f) for f in OWNER_FIELDS if props.get(f)), None)
            if email and oid:
                email_owner_id[email] = oid
        time.sleep(0.2)

    if owners_scope_ok:
        return {e: owner_id_to_ae.get(oid, f"Unmapped owner id {oid}") for e, oid in email_owner_id.items()}
    return {e: f"Owner id {oid} (name unresolved -- HubSpot key lacks Owners scope)" for e, oid in email_owner_id.items()}


# --------------------------------------------------------------- Main

def main():
    with open(INPUT_CSV, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    log(f"Loaded {len(rows)} contacts from {INPUT_CSV.name}")

    emails = sorted({r["Email"].strip().lower() for r in rows if r.get("Email", "").strip()})
    linkedin_urls = sorted({norm_url(r["LinkedIn Url"]) for r in rows if r.get("LinkedIn Url", "").strip()})
    log(f"Matchable: {len(emails)} unique emails, {len(linkedin_urls)} unique LinkedIn URLs")

    log("Step 1/3: Smartlead exact touchpoint lookup...")
    sl_results = run_smartlead(emails)
    matched_sl = sum(1 for v in sl_results.values() if v.get("matched"))
    log(f"  Smartlead matched {matched_sl}/{len(emails)} emails")
    with open(OUT_DIR / "_raw_smartlead_results.json", "w") as f:
        json.dump({k: {**v, "last_touch": str(v.get("last_touch")) if v.get("last_touch") else None}
                    for k, v in sl_results.items()}, f, indent=1)

    log("Step 2/3: HeyReach touchpoint lookup...")
    hr_results = build_heyreach_activity(set(linkedin_urls))
    matched_hr = sum(1 for v in hr_results.values() if v.get("matched"))
    log(f"  HeyReach matched {matched_hr}/{len(linkedin_urls)} LinkedIn URLs")
    with open(OUT_DIR / "_raw_heyreach_results.json", "w") as f:
        json.dump({k: {**v, "last_touch": str(v.get("last_touch")) if v.get("last_touch") else None}
                    for k, v in hr_results.items()}, f, indent=1)

    log("Step 3/3: HubSpot AE ownership (all matched emails, not sampled)...")
    ae_map = hubspot_ae_lookup(emails)
    log(f"  AE/SDR owner found for {len(ae_map)}/{len(emails)} emails")
    with open(OUT_DIR / "_raw_hubspot_ae.json", "w") as f:
        json.dump(ae_map, f, indent=1)

    log("Assembling final CSV...")
    out_rows = []
    for r in rows:
        email = r.get("Email", "").strip().lower()
        lurl = norm_url(r.get("LinkedIn Url", ""))

        sl = sl_results.get(email, {}) if email else {}
        hr = hr_results.get(lurl, {}) if lurl else {}

        sl_touch = sl.get("touches", 0) if sl.get("matched") else 0
        hr_touch = hr.get("touches", 0) if hr.get("matched") else 0
        total_touch = sl_touch + hr_touch

        last_dates = [d for d in [sl.get("last_touch"), hr.get("last_touch")] if d]
        last_outreach = max(last_dates).date().isoformat() if last_dates else ""

        responded = sl.get("replied") or hr.get("replied")
        ooo_only = (sl.get("replied_but_ooo_only") or hr.get("replied_but_ooo_only")) and not responded
        if responded:
            resp_status = "Yes"
        elif ooo_only:
            resp_status = "No (OOO auto-reply only, excluded)"
        elif email and not sl.get("matched") and lurl and not hr.get("matched"):
            resp_status = "Not checked (no match)"
        elif not email and not lurl:
            resp_status = "Not checked (no email/LinkedIn on file)"
        else:
            resp_status = "No"

        ae = ae_map.get(email, "") if email else ""
        is_us_ae = "Yes" if ae in AE_NAMES else ("SDR" if ae in SDR_NAMES else "")

        match_status = []
        if email:
            match_status.append("email-matched" if sl.get("matched") else "email-not-found-in-smartlead")
        else:
            match_status.append("no-email")
        if lurl:
            match_status.append("linkedin-matched" if hr.get("matched") else "linkedin-not-found-in-heyreach")
        else:
            match_status.append("no-linkedin")

        out = dict(r)
        out["SL_Touch_Points"] = sl_touch
        out["HR_Touch_Points"] = hr_touch
        out["Total_Touch_Points"] = total_touch
        out["Last_Outreach"] = last_outreach
        out["Responded_Excl_OOO"] = resp_status
        out["Campaign_Sources"] = "; ".join((sl.get("campaigns") or []) + (hr.get("campaigns") or []))[:500]
        out["Reply_Detail"] = " | ".join(x for x in [sl.get("reply_detail"), hr.get("reply_detail")] if x)
        out["AE_Owner"] = ae
        out["Is_US_AE"] = is_us_ae
        out["Match_Status"] = "; ".join(match_status)
        out_rows.append(out)

    out_path = OUT_DIR / "events-us-outreach-audit.csv"
    fieldnames = list(rows[0].keys())
    for col in ["SL_Touch_Points", "HR_Touch_Points", "Total_Touch_Points", "Last_Outreach",
                "Responded_Excl_OOO", "Campaign_Sources", "Reply_Detail", "AE_Owner", "Is_US_AE", "Match_Status"]:
        if col not in fieldnames:
            fieldnames.append(col)
    for legacy in ["Response_Status", "Estimation_Method"]:
        if legacy in fieldnames:
            fieldnames.remove(legacy)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(out_rows)

    log(f"\n=== DONE ===")
    log(f"Output: {out_path}")
    log(f"Total contacts: {len(out_rows)}")
    log(f"With any touchpoint: {sum(1 for o in out_rows if o['Total_Touch_Points'] > 0)}")
    log(f"Responded (excl OOO): {sum(1 for o in out_rows if o['Responded_Excl_OOO'] == 'Yes')}")
    log(f"With a US AE/SDR owner: {sum(1 for o in out_rows if o['Is_US_AE'] in ('Yes', 'SDR'))}")


if __name__ == "__main__":
    main()
