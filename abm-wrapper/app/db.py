"""Local SQLite storage for the abm-wrapper app.

Two tables, two very different privacy postures:

- `resolved_domains` -- non-sensitive, reusable facts (company name -> domain).
  Tracked in git on purpose: it's just public company/domain facts, so every
  teammate benefits from prior lookups instead of re-spending on repeats.
- `excluded_leads` -- real names/emails/reasons. The user explicitly confirmed
  (after being shown the tradeoff -- this repo otherwise treats prospect PII
  as never-commit, e.g. the HubSpot exclusion cache) that this should be
  committed to git too, so exclusion history is shared across the team. That
  is a deliberate override of the usual convention, not an oversight.
"""
import re
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "domain_cache.db"


def _normalize_company(name):
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def _connect():
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


def record_exclusions(run_id, rows, source, email_key="Email", company_key="Cleaned Company",
                       first_key="Cleaned First Name", last_key="Cleaned Last Name",
                       reason_key="Exclusion Reason"):
    """Persist one row per excluded lead. `source` distinguishes which filter
    excluded it: 'title_filter' / 'dnu_list' / 'personal_email_policy'."""
    if not rows:
        return
    conn = _connect()
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


def get_cached_domain(company_name):
    key = _normalize_company(company_name)
    if not key:
        return None
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT domain FROM resolved_domains WHERE company_key = ?", (key,)
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def store_resolved_domain(company_name, domain, source):
    key = _normalize_company(company_name)
    if not key or not domain:
        return
    conn = _connect()
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
