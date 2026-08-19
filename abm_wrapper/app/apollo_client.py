"""Apollo + Clearbit calls for Domain Resolution and People Discovery.

The sibling nac_outbound_kit reference kit's scripts call `v1/mixed_people/search`
as "search-only, no credit spend" -- confirmed live against this repo's real
Apollo key that this endpoint is now DEPRECATED (HTTP 422). Verified against
Apollo's current docs (docs.apollo.io) and switched to the current endpoints:

- People search: POST /api/v1/mixed_people/api_search -- still 0 credits, but the
  response only gives first_name/last_name_obfuscated/title/has_email, NOT an
  actual email or LinkedIn URL. Revealing the real email is a separate, credit-
  consuming call (Step 5, not built yet).
- Organization search: POST /api/v1/mixed_companies/search -- DOES consume
  Apollo credits (1 per page). Per the user's explicit choice, this is NOT
  used for Domain Resolution's fallback step anymore -- see resolve_domain()
  below, which uses the local cache + Claude/web-search fallback instead
  (domain_resolver_ai.py). Kept here only for People Discovery's own use of
  the Apollo API; not called by the domain waterfall.
"""
import time

import requests

from . import db, domain_resolver_ai
from .config import APOLLO_API_KEY, PUBLIC_BASE_URL

APOLLO_BASE = "https://api.apollo.io/api/v1"
_HEADERS = {"Content-Type": "application/json", "Cache-Control": "no-cache"}


def clearbit_autocomplete(company_name):
    """Free, no-auth lookup -- first step of the Domain Resolution waterfall."""
    if not company_name:
        return None
    try:
        resp = requests.get(
            "https://autocomplete.clearbit.com/v1/companies/suggest",
            params={"query": company_name},
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        results = resp.json()
        return results[0].get("domain") if results else None
    except Exception:
        return None


def search_organization_domain(company_name):
    """Apollo organization search -- fallback step of the Domain Resolution
    waterfall. Costs 1 Apollo credit per page -- only call this when the
    caller has explicitly opted into spending credits (Clearbit failed)."""
    if not company_name or not APOLLO_API_KEY:
        return None
    try:
        resp = requests.post(
            f"{APOLLO_BASE}/mixed_companies/search",
            headers=_HEADERS,
            json={"api_key": APOLLO_API_KEY, "q_organization_name": company_name, "per_page": 1},
            timeout=20,
        )
        if resp.status_code != 200:
            return None
        # Confirmed live: this endpoint returns the match list under
        # "accounts", not "organizations" (despite the endpoint name) --
        # checking both defensively in case Apollo's response shape varies.
        body = resp.json()
        orgs = body.get("accounts") or body.get("organizations") or []
        if not orgs:
            return None
        return orgs[0].get("primary_domain") or orgs[0].get("domain") or orgs[0].get("website_url")
    except Exception:
        return None


def resolve_domain(company_name, use_ai_fallback=False, use_apollo_fallback=False):
    """(domain, source) -- local cache first (free, instant, shared via git),
    then free Clearbit, then Claude + grounded web search if the caller opts
    in (small per-lookup cost, needs ANTHROPIC_API_KEY), then Apollo org
    search as a last resort if the caller opts into that too (costs 1 Apollo
    credit per company -- the priciest step in the waterfall, which is why
    it only runs after the two free/cheap ones have both failed)."""
    cached = db.get_cached_domain(company_name)
    if cached:
        return cached, "cache"

    domain = clearbit_autocomplete(company_name)
    if domain:
        db.store_resolved_domain(company_name, domain, "clearbit")
        return domain, "clearbit"

    if use_ai_fallback:
        domain = domain_resolver_ai.resolve_domain_via_web_search(company_name)
        if domain:
            db.store_resolved_domain(company_name, domain, "claude")
            return domain, "claude"

    if use_apollo_fallback:
        domain = search_organization_domain(company_name)
        if domain:
            db.store_resolved_domain(company_name, domain, "apollo")
            return domain, "apollo"

    return None, None


def search_people(domain, titles, employee_ranges=None, locations=None, per_page=25):
    """mixed_people/api_search -- 0 credits, but the response has no email or
    LinkedIn URL (just name/title/has_email) -- see module docstring."""
    if not APOLLO_API_KEY or not domain:
        return []
    payload = {
        "api_key": APOLLO_API_KEY,
        "q_organization_domains_list": [domain],
        "person_titles": titles,
        "per_page": per_page,
        "page": 1,
    }
    if employee_ranges:
        payload["organization_num_employees_ranges"] = employee_ranges
    if locations:
        payload["person_locations"] = locations

    for attempt in range(3):
        try:
            resp = requests.post(f"{APOLLO_BASE}/mixed_people/api_search", headers=_HEADERS, json=payload, timeout=30)
        except Exception:
            return []
        if resp.status_code == 429:
            time.sleep(30 * (attempt + 1))
            continue
        if resp.status_code != 200:
            return []
        return resp.json().get("people", [])
    return []


def reveal_email(apollo_id=None, domain=None, first_name=None, last_name=None, organization_name=None):
    """POST /api/v1/people/match with reveal_personal_emails=true -- confirmed
    against Apollo's current docs, synchronous. Costs 1 credit for a match
    with email (0 if nothing found; +8 more only if a phone also comes back,
    which we don't request here). Prefers `apollo_id` (the exact record from
    Step 4's search) over name-based matching, since Step 4's name may be
    partially obfuscated.

    Returns {"email": str, "email_status": str} or None if nothing revealed.
    """
    if not APOLLO_API_KEY:
        return None
    payload = {"api_key": APOLLO_API_KEY, "reveal_personal_emails": True}
    if apollo_id:
        payload["id"] = apollo_id
    else:
        if not (first_name and (domain or organization_name)):
            return None
        payload["first_name"] = first_name
        if last_name:
            payload["last_name"] = last_name
        if domain:
            payload["domain"] = domain
        if organization_name:
            payload["organization_name"] = organization_name

    try:
        resp = requests.post(f"{APOLLO_BASE}/people/match", headers=_HEADERS, json=payload, timeout=30)
    except Exception:
        return None
    if resp.status_code != 200:
        return None

    match = resp.json().get("person")
    if not match or not match.get("email"):
        return None
    return {"email": match["email"], "email_status": match.get("email_true_status", "") or match.get("email_status", "")}


def reveal_phone(apollo_id=None, domain=None, first_name=None, last_name=None, organization_name=None):
    """POST /api/v1/people/match with reveal_phone_number=true -- Apollo
    delivers the actual number ASYNCHRONOUSLY to `webhook_url` (their docs:
    "can take several minutes"), not in this response. Without a public URL
    this app can't receive that callback, so this returns None immediately
    without even making the (credit-costing) call when PUBLIC_BASE_URL isn't
    configured -- no point spending credits on a request whose result we can
    never receive. Once ABM_WRAPPER_PUBLIC_URL is set (app is hosted), this
    starts actually firing requests; the webhook receiver still needs to be
    wired up separately at that point."""
    if not PUBLIC_BASE_URL:
        return None
    if not APOLLO_API_KEY:
        return None
    webhook_url = f"{PUBLIC_BASE_URL.rstrip('/')}/webhooks/apollo-phone"
    payload = {"api_key": APOLLO_API_KEY, "reveal_phone_number": True, "webhook_url": webhook_url}
    if apollo_id:
        payload["id"] = apollo_id
    else:
        if not (first_name and (domain or organization_name)):
            return None
        payload["first_name"] = first_name
        if last_name:
            payload["last_name"] = last_name
        if domain:
            payload["domain"] = domain
        if organization_name:
            payload["organization_name"] = organization_name

    try:
        resp = requests.post(f"{APOLLO_BASE}/people/match", headers=_HEADERS, json=payload, timeout=30)
    except Exception:
        return None
    if resp.status_code != 200:
        return None
    return {"status": "pending", "note": "Apollo will deliver via webhook in a few minutes."}
