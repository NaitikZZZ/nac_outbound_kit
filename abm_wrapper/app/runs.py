import csv
import io
import json
import time
import uuid
from datetime import datetime, timezone

from . import kv

_registry = {}  # local-dev fallback when Redis isn't configured (see kv.py)


class Run:
    def __init__(self, run_id):
        self.id = run_id
        self.headers = []
        self.ok_rows = []
        self.excluded_rows = []
        self.exclusion_ran = False
        self.step_results = {}  # step name -> summary dict, for the UI / GET state
        self.log = []  # activity log: [{ts, message, duration_ms}, ...]
        self.naming_components = {}  # priority/team/use_case/region/channel/poc_name/start_date, set by Step 7
        self.campaign_name = ""

    def add_log(self, message, duration_ms):
        self.log.append({
            "ts": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            "message": message,
            "duration_ms": duration_ms,
        })

    def to_dict(self):
        return {
            "id": self.id,
            "headers": self.headers,
            "ok_rows": self.ok_rows,
            "excluded_rows": self.excluded_rows,
            "exclusion_ran": self.exclusion_ran,
            "step_results": self.step_results,
            "log": self.log,
            "naming_components": self.naming_components,
            "campaign_name": self.campaign_name,
        }

    @classmethod
    def from_dict(cls, data):
        run = cls(data["id"])
        run.headers = data.get("headers", [])
        run.ok_rows = data.get("ok_rows", [])
        run.excluded_rows = data.get("excluded_rows", [])
        run.exclusion_ran = data.get("exclusion_ran", False)
        run.step_results = data.get("step_results", {})
        run.log = data.get("log", [])
        run.naming_components = data.get("naming_components", {})
        run.campaign_name = data.get("campaign_name", "")
        return run


class Timer:
    """`with Timer() as t: ...` then t.ms holds elapsed milliseconds."""

    def __enter__(self):
        self._start = time.monotonic()
        self.ms = 0
        return self

    def __exit__(self, *exc):
        self.ms = int((time.monotonic() - self._start) * 1000)
        return False


def create_run():
    run_id = uuid.uuid4().hex[:12]
    run = Run(run_id)
    if kv.available():
        kv.save_run(run_id, json.dumps(run.to_dict()))
    else:
        _registry[run_id] = run
    return run


def get_run(run_id):
    if kv.available():
        raw = kv.load_run(run_id)
        if raw is None:
            raise KeyError(f"unknown run_id: {run_id}")
        return Run.from_dict(json.loads(raw))
    run = _registry.get(run_id)
    if run is None:
        raise KeyError(f"unknown run_id: {run_id}")
    return run


def save(run):
    """Persist a run's current state. Required after every mutation once
    deployed -- each Vercel request is a fresh, stateless function with no
    shared memory to mutate in place across requests, unlike a local
    long-lived `uvicorn` process. A no-op in local dev without Redis
    configured, since the in-memory registry already holds the live,
    already-mutated object by reference."""
    if kv.available():
        kv.save_run(run.id, json.dumps(run.to_dict()))


def rows_to_csv_bytes(headers, rows):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in headers})
    return buf.getvalue().encode("utf-8-sig")
