"""Domain cache + exclusion audit log, with two backends depending on
whether Redis is configured (see kv.py):

- **Redis available (deployed on Vercel):** all reads/writes go through
  Redis. The committed SQLite file (`data/domain_cache.db`) is still bundled
  in the deployment and used as a read-only seed on a Redis cache miss --
  reads never write back to it (the deployed filesystem outside `/tmp` is
  read-only anyway), so it stays exactly what's committed to git until
  someone regenerates it locally the same way as before.
- **Redis unavailable (local dev):** behaves exactly as before this file was
  rewritten -- the local SQLite file is both the read and write path, so
  running the app locally without any Redis env vars set needs no changes.

Two tables/keyspaces, two very different privacy postures:

- domain cache -- non-sensitive, reusable facts (company name -> domain).
  The SQLite copy is tracked in git on purpose: it's just public
  company/domain facts, so every teammate benefits from prior lookups
  instead of re-spending on repeats.
- exclusion log -- real names/emails/reasons. The user explicitly confirmed
  (after being shown the tradeoff -- this repo otherwise treats prospect PII
  as never-commit, e.g. the HubSpot exclusion cache) that the SQLite
  version of this should be committed to git too. New entries written via
  Redis (i.e. from Vercel-hosted runs) are not automatically folded back
  into that committed file -- see the plan's "explicitly out of scope" note.
"""
import json
import re
import sqlite3
from pathlib import Path

from . import kv

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "domain_cache.db"


def _normalize_company(name):
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def _connect_write():
    """For local dev writes (and any environment with a writable disk).
    Raises sqlite3.OperationalError on a read-only filesystem (e.g. deployed
    serverless without Redis configured yet) -- every write call site catches
    that and skips caching rather than crashing the request."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS resolved_domains (
            company_key TEXT PRIMARY KEY,
            company_name TEXT NOT NULL,
            domain TEXT NOT NULL,
            source TEXT NOT NULL,
            resolved_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS excluded_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            excluded_at TEXT NOT NULL DEFAULT (datetime('now')),
            email TEXT,
            company TEXT,
            first_name TEXT,
            last_name TEXT,
            reason TEXT NOT NULL,
            source TEXT NOT NULL
        )
        """
    )
    return conn


def _connect_read():
    """Read-only open of the bundled seed file, if it exists. Never creates
    the file or any tables -- safe on a read-only deployed filesystem, unlike
    _connect_write(). Returns None if there's nothing to read."""
    if not DB_PATH.exists():
        return None
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)


def _record_exclusions_sqlite(run_id, rows, source, email_key, company_key, first_key, last_key, reason_key):
    try:
        conn = _connect_write()
    except sqlite3.OperationalError:
        return  # read-only filesystem and Redis isn't configured -- nothing to persist to
    try:
        conn.executemany(
            """
            INSERT INTO excluded_leads (run_id, email, company, first_name, last_name, reason, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    run_id,
                    row.get(email_key, ""),
                    row.get(company_key, "") or row.get("Company Name", ""),
                    row.get(first_key, ""),
                    row.get(last_key, ""),
                    row.get(reason_key, "") or source,
                    source,
                )
                for row in rows
            ],
        )
        conn.commit()
    finally:
        conn.close()


def record_exclusions(run_id, rows, source, email_key="Email", company_key="Cleaned Company",
                       first_key="Cleaned First Name", last_key="Cleaned Last Name",
                       reason_key="Exclusion Reason"):
    """Persist one row per excluded lead. `source` distinguishes which filter
    excluded it: 'title_filter' / 'dnu_list' / 'personal_email_policy'."""
    if not rows:
        return
    if not kv.available():
        return _record_exclusions_sqlite(run_id, rows, source, email_key, company_key, first_key, last_key, reason_key)

    for row in rows:
        record = {
            "run_id": run_id,
            "email": row.get(email_key, ""),
            "company": row.get(company_key, "") or row.get("Company Name", ""),
            "first_name": row.get(first_key, ""),
            "last_name": row.get(last_key, ""),
            "reason": row.get(reason_key, "") or source,
            "source": source,
        }
        kv.append_exclusion(json.dumps(record))


def _get_cached_domain_sqlite(key):
    conn = _connect_read()
    if conn is None:
        return None
    try:
        row = conn.execute(
            "SELECT domain FROM resolved_domains WHERE company_key = ?", (key,)
        ).fetchone()
        return row[0] if row else None
    except sqlite3.OperationalError:
        return None  # e.g. no such table -- an unexpected/empty bundled file
    finally:
        conn.close()


def get_cached_domain(company_name):
    key = _normalize_company(company_name)
    if not key:
        return None
    if not kv.available():
        return _get_cached_domain_sqlite(key)

    cached = kv.get_domain(key)
    if cached:
        return json.loads(cached)["domain"]
    return _get_cached_domain_sqlite(key)  # bundled seed, read-only on Vercel


def store_resolved_domain(company_name, domain, source):
    key = _normalize_company(company_name)
    if not key or not domain:
        return
    if not kv.available():
        try:
            conn = _connect_write()
        except sqlite3.OperationalError:
            return  # read-only filesystem and Redis isn't configured -- nothing to persist to
        try:
            conn.execute(
                """
                INSERT INTO resolved_domains (company_key, company_name, domain, source)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(company_key) DO UPDATE SET
                    domain = excluded.domain,
                    source = excluded.source,
                    resolved_at = datetime('now')
                """,
                (key, company_name, domain, source),
            )
            conn.commit()
        finally:
            conn.close()
        return

    kv.store_domain(key, json.dumps({"company_name": company_name, "domain": domain, "source": source}))
