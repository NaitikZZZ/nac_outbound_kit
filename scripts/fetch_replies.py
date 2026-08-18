"""Pull last week's replies from HeyReach (LinkedIn) and Smartlead (email).

Writes raw API dumps + a combined CSV to outputs/.
"""
import json
import os
import socket
import sys
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

# The local resolver fails for these hosts; pin IPs from public DNS.
# SNI and cert validation still use the real hostname, so TLS stays verified.
_PIN = {"api.heyreach.io": "63.186.154.247", "server.smartlead.ai": "104.20.37.149"}
_orig_getaddrinfo = socket.getaddrinfo
socket.getaddrinfo = lambda h, p, *a, **k: _orig_getaddrinfo(_PIN.get(h, h), p, *a, **k)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "outputs")
load_dotenv(os.path.join(ROOT, ".env"))

HR_KEY = os.getenv("HEYREACH_API_KEY")
SL_KEY = os.getenv("SMARTLEAD_API_KEY")

DAYS = int(os.getenv("REPLY_WINDOW_DAYS", "7"))
SINCE = datetime.now(timezone.utc) - timedelta(days=DAYS)


def parse_dt(val):
    if not val:
        return None
    if isinstance(val, (int, float)):
        return datetime.fromtimestamp(val / 1000 if val > 1e11 else val, timezone.utc)
    s = str(val).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def dump(name, obj):
    with open(os.path.join(OUT, name), "w") as f:
        json.dump(obj, f, indent=1, default=str)


# ---------------------------------------------------------------- HeyReach
def heyreach():
    url = "https://api.heyreach.io/api/public/inbox/GetConversationsV2"
    headers = {"X-API-KEY": HR_KEY, "Content-Type": "application/json"}
    convos, offset = [], 0
    while True:
        body = {"filters": {}, "offset": offset, "limit": 100}
        r = requests.post(url, headers=headers, json=body, timeout=90)
        if r.status_code != 200:
            print(f"[heyreach] HTTP {r.status_code}: {r.text[:300]}")
            break
        page = r.json()
        items = page.get("items") or []
        convos.extend(items)
        total = page.get("totalCount", 0)
        print(f"[heyreach] fetched {len(convos)}/{total}")
        offset += 100
        if not items or offset >= total:
            break
    dump("_raw_heyreach_conversations.json", convos)
    if convos:
        print("[heyreach] conversation keys:", list(convos[0].keys()))
        msgs = convos[0].get("messages") or []
        if msgs:
            print("[heyreach] message keys:", list(msgs[0].keys()))
    return convos


# --------------------------------------------------------------- Smartlead
def smartlead():
    base = "https://server.smartlead.ai/api/v1"
    r = requests.get(f"{base}/campaigns", params={"api_key": SL_KEY}, timeout=90)
    r.raise_for_status()
    campaigns = r.json()
    print(f"[smartlead] {len(campaigns)} campaigns")

    replies = []
    for c in campaigns:
        cid, cname = c["id"], c.get("name")
        if c.get("status") == "DRAFTED":
            continue
        offset = 0
        while True:
            rr = requests.get(
                f"{base}/campaigns/{cid}/statistics",
                params={"api_key": SL_KEY, "offset": offset, "limit": 100},
                timeout=90,
            )
            if rr.status_code != 200:
                print(f"[smartlead] {cid} HTTP {rr.status_code}: {rr.text[:200]}")
                break
            payload = rr.json()
            rows = payload.get("data") or []
            if offset == 0 and rows:
                print(f"[smartlead] stat keys ({cname}):", list(rows[0].keys()))
            for row in rows:
                if row.get("reply_time"):
                    row["_campaign_id"] = cid
                    row["_campaign_name"] = cname
                    replies.append(row)
            offset += 100
            if not rows or offset >= int(payload.get("total_stats") or 0):
                break
    dump("_raw_smartlead_replies.json", replies)
    print(f"[smartlead] {len(replies)} total replies (all time)")
    return replies


if __name__ == "__main__":
    print(f"Window: replies since {SINCE.isoformat()} ({DAYS} days)\n")
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which in ("both", "heyreach"):
        heyreach()
    if which in ("both", "smartlead"):
        smartlead()
