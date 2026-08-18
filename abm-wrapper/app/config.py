import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")

APOLLO_API_KEY = os.environ.get("APOLLO_API_KEY", "")
HUBSPOT_API_KEY = os.environ.get("HUBSPOT_API_KEY", "")
HUBSPOT_PORTAL_ID = os.environ.get("HUBSPOT_PORTAL_ID", "")
HEYREACH_API_KEY = os.environ.get("HEYREACH_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Apollo's phone reveal is asynchronous -- it POSTs the result to a webhook URL
# rather than returning it in the response. Empty until this app is actually
# hosted somewhere with a public URL (see abm-wrapper/README.md); Step 6
# degrades gracefully when this is unset rather than making a call Apollo
# can never deliver a result for.
PUBLIC_BASE_URL = os.environ.get("ABM_WRAPPER_PUBLIC_URL", "")

EXCLUSION_CACHE_PATH = REPO_ROOT / ".claude" / "skills" / "hubspot-abm-exclusion" / "cache" / "exclusion_cache.csv"
EXCLUSION_CACHE_META_PATH = EXCLUSION_CACHE_PATH.parent / "meta.json"
