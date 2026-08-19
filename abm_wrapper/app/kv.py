"""Upstash Redis-backed persistence, used only when the app is actually
deployed (Vercel functions are stateless and ephemeral -- nothing in-process
or on local disk survives between requests, unlike a local `uvicorn` process).

Local dev without Redis configured keeps working unchanged: `available()`
returns False and every caller (runs.py, db.py) falls back to its pre-Redis
behavior (in-memory dict, local SQLite file) rather than this module doing
anything silently different.

Reads whichever env var names the Vercel Marketplace "Upstash for Redis"
integration actually injects -- both `UPSTASH_REDIS_REST_*` (Upstash's own
naming) and `KV_REST_API_*` (Vercel's older "Vercel KV" naming, which the
integration sometimes mirrors) are accepted.
"""
import os

_URL = os.environ.get("UPSTASH_REDIS_REST_URL") or os.environ.get("KV_REST_API_URL", "")
_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN") or os.environ.get("KV_REST_API_TOKEN", "")

RUN_TTL_SECONDS = 60 * 60 * 48  # 48h -- abandoned runs expire instead of accumulating forever

_client = None


def available():
    return bool(_URL and _TOKEN)


def _get_client():
    global _client
    if _client is None:
        from upstash_redis import Redis
        _client = Redis(url=_URL, token=_TOKEN)
    return _client


def save_run(run_id, data_json):
    _get_client().set(f"run:{run_id}", data_json, ex=RUN_TTL_SECONDS)


def load_run(run_id):
    return _get_client().get(f"run:{run_id}")


def get_domain(key):
    return _get_client().hget("domain_cache", key)


def store_domain(key, value_json):
    _get_client().hset("domain_cache", key, value_json)


def append_exclusion(record_json):
    _get_client().rpush("exclusions_log", record_json)
