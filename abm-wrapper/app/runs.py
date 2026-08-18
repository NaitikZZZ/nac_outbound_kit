import csv
import io
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

RUNS_DIR = Path(__file__).resolve().parents[1] / "runs"


class Run:
    def __init__(self, run_id):
        self.id = run_id
        self.dir = RUNS_DIR / run_id
        self.dir.mkdir(parents=True, exist_ok=True)
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


class Timer:
    """`with Timer() as t: ...` then t.ms holds elapsed milliseconds."""

    def __enter__(self):
        self._start = time.monotonic()
        self.ms = 0
        return self

    def __exit__(self, *exc):
        self.ms = int((time.monotonic() - self._start) * 1000)
        return False


_registry = {}


def create_run():
    run_id = uuid.uuid4().hex[:12]
    run = Run(run_id)
    _registry[run_id] = run
    return run


def get_run(run_id):
    run = _registry.get(run_id)
    if run is None:
        raise KeyError(f"unknown run_id: {run_id}")
    return run


def rows_to_csv_bytes(headers, rows):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in headers})
    return buf.getvalue().encode("utf-8-sig")
