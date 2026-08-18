"""Grounded domain resolution via the Anthropic API's server-side web_search
tool -- the user's chosen replacement for Apollo's paid organization search
as the Clearbit fallback (Apollo org search costs 1 credit/page; this costs
a small amount of Anthropic API + web-search-tool usage instead, roughly
$0.01-0.02/lookup, mostly the $10-per-1,000-searches web search fee -- Haiku
4.5 token cost is negligible for a prompt this short).

Grounded in a real search every time, not model memory, so it doesn't
hallucinate a wrong domain the way asking the model to recall one from
training data would.

Requires ANTHROPIC_API_KEY in .env. Returns None (not an error) if the key
isn't set yet, so the app degrades to "unresolved" rather than crashing.
"""
import re

from .config import ANTHROPIC_API_KEY

_DOMAIN_RE = re.compile(
    r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$"
)


def resolve_domain_via_web_search(company_name):
    if not ANTHROPIC_API_KEY or not company_name:
        return None
    try:
        import anthropic
    except ImportError:
        return None

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=256,
            tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 2, "allowed_callers": ["direct"]}],
            messages=[
                {
                    "role": "user",
                    "content": (
                        f'Search the web to find the official website domain for the '
                        f'company "{company_name}". Do not guess from memory -- confirm '
                        f"with a search. Reply with ONLY the bare domain (e.g. "
                        f"example.com), no protocol, no www, no extra words. If you "
                        f"cannot confirm a domain, reply with exactly: NONE"
                    ),
                }
            ],
        )
    except Exception:
        return None

    text_blocks = [b.text.strip() for b in response.content if b.type == "text" and b.text.strip()]
    if not text_blocks:
        return None

    candidate = text_blocks[-1].strip().strip(".").lower()
    candidate = re.sub(r"^https?://", "", candidate)
    candidate = re.sub(r"^www\.", "", candidate)
    candidate = candidate.split()[0] if candidate else ""

    if candidate == "none" or not _DOMAIN_RE.match(candidate):
        return None
    return candidate
