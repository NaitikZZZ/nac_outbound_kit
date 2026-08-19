import csv
import io
from pathlib import Path

import openpyxl
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from . import apollo_taxonomy, copy_agent, db, exclusion_cache_refresh, naming, runs, skills_bridge
from .config import ANTHROPIC_API_KEY, HUBSPOT_API_KEY
from .steps import step1_input_normalization as step1
from .steps import step2_domain_resolution as step2
from .steps import step3_exclusion_check as step3
from .steps import step4_people_discovery as step4
from .steps import step5_email_reveal as step5
from .steps import step6_phone_reveal as step6
from .steps import step7_output_files as step7
from .steps import step8_associations as step8
from .steps import step9_upload as step9

NAMING_OPTIONS = {
    "priority": ["P0", "P1", "P2", "P3"],
    "team": ["EVENTS", "PRTNR", "API", "ABM"],
    "use_case": ["GRHIGH", "ENT500", "PASSDEAL", "ACTDEAL", "DREAM", "BFSI", "RETAIL",
                 "PREEVENT", "POSTEVENT", "INTENT", "IPANON", "FUNDING", "EXECHIRE"],
    "region": ["KSA", "IDN", "US", "GCC", "AFR", "IND", "PHL", "UKEU"],
    "channel": ["EMAIL", "LI", "WA", "CALL"],
}

APP_DIR = Path(__file__).resolve().parent
BASE_DIR = APP_DIR.parent

app = FastAPI(title="ABM Wrapper")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    return (BASE_DIR / "templates" / "index.html").read_text(encoding="utf-8")


def _read_upload_xlsx(raw_bytes):
    wb = openpyxl.load_workbook(io.BytesIO(raw_bytes), read_only=True, data_only=True)
    sheet = wb.active
    rows_iter = sheet.iter_rows(values_only=True)
    try:
        header_row = next(rows_iter)
    except StopIteration:
        return [], []
    headers = [str(h).strip() if h is not None else "" for h in header_row]
    rows = []
    for raw_row in rows_iter:
        if all(v is None for v in raw_row):
            continue
        row = {}
        for h, v in zip(headers, raw_row):
            if not h:
                continue
            row[h] = "" if v is None else str(v)
        rows.append(row)
    return headers, rows


def _read_upload_csv(raw_bytes):
    text = raw_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    try:
        headers = reader.fieldnames or []
        rows = [dict(r) for r in reader]
    except csv.Error as exc:
        raise HTTPException(
            400,
            f"Could not parse this as a CSV file ({exc}). If this is actually an Excel "
            "file, make sure it's saved with a .xlsx extension so it's read correctly.",
        )
    return headers, rows


def _read_upload_file(filename, raw_bytes):
    if (filename or "").lower().endswith((".xlsx", ".xlsm")):
        try:
            return _read_upload_xlsx(raw_bytes)
        except Exception as exc:
            raise HTTPException(400, f"Could not read this as an Excel file: {exc}")
    return _read_upload_csv(raw_bytes)


@app.post("/api/runs")
def create_run():
    run = runs.create_run()
    return {"run_id": run.id}


@app.post("/api/runs/{run_id}/upload")
async def upload(run_id: str, file: UploadFile = File(...)):
    run = _get_run_or_404(run_id)
    raw = await file.read()
    headers, rows = _read_upload_file(file.filename, raw)
    if not headers:
        raise HTTPException(400, "Could not read any columns from that file.")

    with runs.Timer() as t:
        result = step1.run(headers, rows)
    run.headers = result["headers"]
    run.ok_rows = result["rows"]
    run.excluded_rows = []
    run.step_results["step1"] = {k: v for k, v in result.items() if k != "rows"}
    run.add_log(f"Upload & normalize: {result['row_count']} rows", t.ms)
    runs.save(run)
    return {"preview": result["rows"][:20], **run.step_results["step1"]}


@app.post("/api/runs/{run_id}/steps/domain-resolution")
def domain_resolution(run_id: str, run_step: bool = Form(...), use_ai_fallback: bool = Form(False),
                       use_apollo_fallback: bool = Form(False)):
    run = _get_run_or_404(run_id)
    _require_step(run, "step1")
    cols = run.step_results["step1"]["detected_columns"]

    if not run_step:
        run.step_results["step2"] = {"skipped": True, "reason": "Skipped by user choice"}
        run.add_log("Domain resolution: skipped by user", 0)
        runs.save(run)
        return run.step_results["step2"]

    if step2.should_skip(run.headers, run.ok_rows):
        run.step_results["step2"] = {"skipped": True, "reason": "Domain/Website already filled on every row"}
        run.add_log("Domain resolution: auto-skipped (already filled)", 0)
        runs.save(run)
        return run.step_results["step2"]

    with runs.Timer() as t:
        result = step2.run(run.headers, run.ok_rows, cols, use_ai_fallback, use_apollo_fallback)
    run.headers = result["headers"]
    run.ok_rows = result["rows"]
    run.step_results["step2"] = {k: v for k, v in result.items() if k != "rows"}
    run.step_results["step2"]["skipped"] = False
    run.add_log(
        f"Domain resolution: {result['newly_resolved']} resolved of {result['row_count']} rows",
        t.ms,
    )
    runs.save(run)
    return {"preview": result["rows"][:20], **run.step_results["step2"]}


@app.get("/api/runs/{run_id}/titles")
def titles(run_id: str):
    run = _get_run_or_404(run_id)
    _require_step(run, "step1")
    cols = run.step_results["step1"]["detected_columns"]
    return {"titles": step3.distinct_titles(run.headers, run.ok_rows, cols)}


@app.post("/api/runs/{run_id}/steps/title-exclusion")
def title_exclusion(run_id: str, excluded_titles: list[str] = Form(default=[])):
    run = _get_run_or_404(run_id)
    _require_step(run, "step1")
    cols = run.step_results["step1"]["detected_columns"]

    with runs.Timer() as t:
        kept, excluded = step3.apply_title_exclusion(run.id, run.headers, run.ok_rows, cols, excluded_titles)
    run.ok_rows = kept
    run.excluded_rows = run.excluded_rows + excluded
    run.add_log(f"Title exclusion: {len(excluded)} rows excluded", t.ms)
    runs.save(run)
    return {"excluded_count": len(excluded), "remaining_ok": len(kept)}


@app.post("/api/runs/{run_id}/steps/exclusion-check")
def exclusion_check(run_id: str, run_check: bool = Form(...)):
    run = _get_run_or_404(run_id)
    _require_step(run, "step1")

    with runs.Timer() as t:
        result = step3.run(run.id, run.headers, run.ok_rows, run_check)
    run.ok_rows = result["ok_rows"]
    run.excluded_rows = run.excluded_rows + result["excluded_rows"]
    run.exclusion_ran = result["ran"]
    run.step_results["step3"] = {k: v for k, v in result.items() if k not in ("ok_rows", "excluded_rows")}
    run.add_log(
        f"DNU exclusion check: {result['ok_count']} OK / {result['excluded_count']} excluded"
        if result["ran"] else "DNU exclusion check: skipped by user",
        t.ms,
    )
    runs.save(run)
    return {
        "preview_ok": run.ok_rows[:20],
        "preview_excluded": run.excluded_rows[:20],
        **run.step_results["step3"],
    }


@app.get("/api/runs/{run_id}/apollo-taxonomy")
def taxonomy(run_id: str):
    _get_run_or_404(run_id)
    return {
        "seniorities": apollo_taxonomy.SENIORITIES,
        "employee_buckets": apollo_taxonomy.EMPLOYEE_SIZE_BUCKETS,
        "default_regions": apollo_taxonomy.DEFAULT_REGIONS,
        "default_titles": skills_bridge.default_people_discovery_titles(),
    }


@app.post("/api/runs/{run_id}/steps/people-discovery")
def people_discovery(run_id: str, run_step: bool = Form(...), work_email_only: bool = Form(False),
                      seniorities: list[str] = Form(default=[]), employee_range: str = Form(""),
                      regions: str = Form(""), titles: str = Form("")):
    run = _get_run_or_404(run_id)
    _require_step(run, "step1")
    cols = run.step_results["step1"]["detected_columns"]
    domain_col = run.step_results.get("step2", {}).get("resolved_column")

    if not run_step:
        run.step_results["step4"] = {"skipped": True, "reason": "Skipped by user choice"}
        run.add_log("People discovery: skipped by user", 0)
        runs.save(run)
        return run.step_results["step4"]

    if step4.should_skip_all(run.headers, run.ok_rows, cols):
        run.step_results["step4"] = {"skipped": True, "reason": "Email already filled on every row"}
        run.add_log("People discovery: auto-skipped (email already filled)", 0)
        runs.save(run)
        return run.step_results["step4"]

    employee_ranges = [employee_range] if employee_range else None
    location_list = [r.strip() for r in regions.split(",") if r.strip()] or None
    title_list = [t.strip() for t in titles.split(",") if t.strip()] or None
    seniority_list = [s for s in seniorities if s] or None

    with runs.Timer() as t:
        result = step4.run(run.headers, run.ok_rows, cols, domain_col, title_list, employee_ranges,
                            location_list, work_email_only)
    run.headers = result["headers"]
    run.ok_rows = result["rows"]
    if result["excluded_rows"]:
        db.record_exclusions(run.id, result["excluded_rows"], source="personal_email_policy")
        run.excluded_rows = run.excluded_rows + result["excluded_rows"]
    run.step_results["step4"] = {k: v for k, v in result.items() if k not in ("rows", "excluded_rows")}
    run.step_results["step4"]["skipped"] = False
    run.step_results["step4"]["seniorities_used"] = seniority_list
    run.add_log(
        f"People discovery: {result['counts']['discovered']} discovered, "
        f"{result['counts']['excluded_personal_only']} excluded (personal-only)",
        t.ms,
    )
    runs.save(run)
    return {"preview": result["rows"][:20], **run.step_results["step4"]}


@app.get("/api/runs/{run_id}/state")
def state(run_id: str):
    run = _get_run_or_404(run_id)
    return {
        "run_id": run.id,
        "headers": run.headers,
        "ok_count": len(run.ok_rows),
        "excluded_count": len(run.excluded_rows),
        "steps": run.step_results,
        "log": run.log,
    }


@app.get("/api/runs/{run_id}/rows/{track}")
def rows(run_id: str, track: str):
    run = _get_run_or_404(run_id)
    if track == "ok":
        data = run.ok_rows
    elif track == "excluded":
        data = run.excluded_rows
    else:
        raise HTTPException(404, "unknown track")
    headers = run.headers + (["Exclusion Reason"] if track == "excluded" and "Exclusion Reason" not in run.headers else [])
    return {"headers": headers, "rows": data}


@app.get("/api/runs/{run_id}/download/{track}")
def download(run_id: str, track: str):
    run = _get_run_or_404(run_id)
    if track == "ok":
        data = run.ok_rows
    elif track == "excluded":
        data = run.excluded_rows
    else:
        raise HTTPException(404, "unknown track")
    headers = run.headers + (["Exclusion Reason"] if track == "excluded" and "Exclusion Reason" not in run.headers else [])
    body = runs.rows_to_csv_bytes(headers, data)
    return Response(
        content=body,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{run_id}-{track}.csv"'},
    )


@app.get("/api/runs/{run_id}/steps/email-reveal/estimate")
def email_reveal_estimate(run_id: str):
    """Row count needing a reveal, shown to the user before they confirm --
    this step spends real Apollo credits (1 per person found, 0 if not)."""
    run = _get_run_or_404(run_id)
    _require_step(run, "step1")
    return {"rows_needing_reveal": step5.count_needing_reveal(run.ok_rows)}


@app.post("/api/runs/{run_id}/steps/email-reveal")
def email_reveal(run_id: str, run_step: bool = Form(...)):
    run = _get_run_or_404(run_id)
    _require_step(run, "step1")
    domain_col = run.step_results.get("step2", {}).get("resolved_column")

    if not run_step:
        run.step_results["step5"] = {"skipped": True, "reason": "Skipped by user choice"}
        run.add_log("Email reveal: skipped by user", 0)
        runs.save(run)
        return run.step_results["step5"]

    with runs.Timer() as t:
        result = step5.run(run.headers, run.ok_rows, domain_col)
    run.headers = result["headers"]
    run.ok_rows = result["rows"]
    run.step_results["step5"] = {k: v for k, v in result.items() if k != "rows"}
    run.step_results["step5"]["skipped"] = False
    run.add_log(f"Email reveal: {result['counts']['revealed']} revealed (real Apollo credits spent)", t.ms)
    runs.save(run)
    return {"preview": result["rows"][:20], **run.step_results["step5"]}


@app.post("/api/runs/{run_id}/steps/phone-reveal")
def phone_reveal(run_id: str, run_step: bool = Form(...)):
    run = _get_run_or_404(run_id)
    _require_step(run, "step1")
    domain_col = run.step_results.get("step2", {}).get("resolved_column")

    if not run_step:
        run.step_results["step6"] = {"skipped": True, "reason": "Skipped by user choice -- phone enrichment is opt-in every run"}
        run.add_log("Phone reveal: skipped by user", 0)
        runs.save(run)
        return run.step_results["step6"]

    with runs.Timer() as t:
        result = step6.run(run.headers, run.ok_rows, domain_col)
    run.headers = result["headers"]
    run.ok_rows = result["rows"]
    run.step_results["step6"] = {k: v for k, v in result.items() if k != "rows"}
    run.step_results["step6"]["skipped"] = False
    run.add_log(f"Phone reveal: {result.get('pending', 0)} pending / {result.get('attempted', 0)} attempted", t.ms)
    runs.save(run)
    return {"preview": result["rows"][:20], **run.step_results["step6"]}


@app.get("/api/runs/{run_id}/naming-options")
def naming_options(run_id: str):
    _get_run_or_404(run_id)
    return NAMING_OPTIONS


@app.post("/api/runs/{run_id}/steps/output-files")
def output_files(run_id: str, priority: str = Form(...), team: str = Form(...), use_case: str = Form(...),
                  region: str = Form(...), channel: str = Form(...), poc_name: str = Form(...),
                  start_date: str = Form(...)):
    run = _get_run_or_404(run_id)
    _require_step(run, "step1")

    campaign_name = naming.build_campaign_name(priority, team, use_case, region, channel, poc_name, start_date)
    run.naming_components = {
        "priority": priority, "team": team, "use_case": use_case, "region": region,
        "channel": channel, "poc_name": poc_name, "start_date": start_date,
    }
    run.campaign_name = campaign_name

    with runs.Timer() as t:
        result = step7.run(run.headers, run.ok_rows, campaign_name)
    run.headers = result["headers"]
    run.ok_rows = result["rows"]
    run.step_results["step7"] = {k: v for k, v in result.items() if k not in ("rows", "heyreach_leads")}
    run.add_log(f"Output files: {result['counts']}", t.ms)
    runs.save(run)
    return run.step_results["step7"]


@app.post("/api/runs/{run_id}/steps/output-files/push-heyreach")
def push_heyreach(run_id: str, confirm: bool = Form(...)):
    """The plan's first real external write. Requires explicit confirm=true
    from the UI, shown alongside the exact list name + lead count first."""
    run = _get_run_or_404(run_id)
    _require_step(run, "step7")
    if not confirm:
        raise HTTPException(400, "Confirmation required before pushing to HeyReach.")

    result = step7.run(run.headers, run.ok_rows, run.campaign_name)
    with runs.Timer() as t:
        push_result = step7.push_to_heyreach(run.campaign_name, result["heyreach_leads"])
    run.step_results["step7_heyreach"] = push_result
    run.add_log(f"HeyReach push: {push_result.get('added', 0)} added, {push_result.get('failed', 0)} failed", t.ms)
    runs.save(run)
    return push_result


@app.get("/api/runs/{run_id}/steps/associations")
def associations(run_id: str):
    run = _get_run_or_404(run_id)
    with runs.Timer() as t:
        result = step8.run()
    run.step_results["step8"] = result
    run.add_log(f"Associations: {len(result['projects'])} projects, {len(result['partners'])} partners, {len(result['events'])} events", t.ms)
    runs.save(run)
    return result


@app.post("/api/runs/{run_id}/steps/upload/preview")
def upload_preview(run_id: str, track: str = Form(...)):
    run = _get_run_or_404(run_id)
    _require_step(run, "step1")
    cols = run.step_results["step1"]["detected_columns"]

    if track == "ok":
        return step9.preview(run.ok_rows, cols, run.campaign_name)
    elif track == "farming":
        farming_name = naming.build_campaign_name(**run.naming_components, farming=True) if run.naming_components else "FARMING"
        return step9.preview(run.excluded_rows, cols, farming_name)
    raise HTTPException(404, "unknown track")


@app.post("/api/runs/{run_id}/steps/upload/execute")
def upload_execute(run_id: str, track: str = Form(...), confirm: bool = Form(...),
                    association_object_type: str = Form(""), association_object_id: str = Form("")):
    """The plan's highest-blast-radius write -- the shared HubSpot CRM.
    Requires explicit confirm=true, per upload, shown alongside the exact
    contact count and campaign/list name first."""
    run = _get_run_or_404(run_id)
    _require_step(run, "step1")
    if not confirm:
        raise HTTPException(400, "Confirmation required before uploading to HubSpot.")
    cols = run.step_results["step1"]["detected_columns"]
    association = {"object_type": association_object_type, "object_id": association_object_id} if association_object_id else None

    with runs.Timer() as t:
        if track == "ok":
            result = step9.execute(run.ok_rows, cols, run.campaign_name, association)
        elif track == "farming":
            farming_name = naming.build_campaign_name(**run.naming_components, farming=True) if run.naming_components else "FARMING"
            result = step9.execute(run.excluded_rows, cols, farming_name, association=None)
        else:
            raise HTTPException(404, "unknown track")
    run.step_results[f"step9_{track}"] = result
    run.add_log(f"HubSpot upload ({track}): {result.get('upserted_count', 0)} contacts to '{result['campaign_name']}'", t.ms)
    runs.save(run)
    return result


@app.get("/api/runs/{run_id}/steps/copy-agent/estimate")
def copy_agent_estimate(run_id: str):
    """Free preview: how leads would segment, before spending anything on
    generation. Segmentation itself is local (no API call)."""
    run = _get_run_or_404(run_id)
    _require_step(run, "step1")
    cols = run.step_results["step1"]["detected_columns"]
    title_col = cols.get("title")
    segments = copy_agent.segment_leads(run.ok_rows, title_col)
    top = segments[:copy_agent.MAX_SEGMENTS]
    dropped = segments[copy_agent.MAX_SEGMENTS:]
    return {
        "anthropic_key_set": bool(ANTHROPIC_API_KEY),
        "segments": [{"label": s["family"]["label"], "lead_count": len(s["leads"])} for s in top],
        "dropped_segment_count": len(dropped),
        "dropped_lead_count": sum(len(s["leads"]) for s in dropped),
        "total_leads": len(run.ok_rows),
    }


@app.post("/api/runs/{run_id}/steps/copy-agent")
def copy_agent_step(run_id: str, run_step: bool = Form(...)):
    """Step 10, modeled on the reference tool's Copy Agent: segments OK
    leads by persona and generates email + LinkedIn copy per segment.
    Degrades to a clean skip if ANTHROPIC_API_KEY isn't set, matching the
    reference tool's own behavior, rather than erroring."""
    run = _get_run_or_404(run_id)
    _require_step(run, "step1")
    cols = run.step_results["step1"]["detected_columns"]
    poc_name = run.naming_components.get("poc_name", "") if run.naming_components else ""

    if not run_step:
        run.step_results["step10"] = {"skipped": True, "reason": "Skipped by user choice"}
        run.add_log("Copy Agent: skipped by user", 0)
        runs.save(run)
        return run.step_results["step10"]

    if not ANTHROPIC_API_KEY:
        run.step_results["step10"] = {"skipped": True, "reason": "ANTHROPIC_API_KEY not set -- Copy Agent skipped"}
        run.add_log("Copy Agent: ANTHROPIC_API_KEY not set - Copy Agent skipped", 0)
        runs.save(run)
        return run.step_results["step10"]

    with runs.Timer() as t:
        result = copy_agent.run(run.ok_rows, cols, poc_name)
    result["skipped"] = False
    run.step_results["step10"] = result
    run.add_log(
        f"Copy Agent: generated copy for {len(result['segments'])} segment(s) covering "
        f"{sum(s['lead_count'] for s in result['segments'])} of {result['total_leads']} lead(s)",
        t.ms,
    )
    runs.save(run)
    return result


@app.get("/api/runs/{run_id}/steps/copy-agent/download")
def download_copy_agent(run_id: str):
    run = _get_run_or_404(run_id)
    result = run.step_results.get("step10")
    if not result or result.get("skipped"):
        raise HTTPException(404, "Copy Agent has not produced output for this run")
    body = copy_agent.to_markdown(result, run.campaign_name or run_id)
    return Response(
        content=body.encode("utf-8"),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{run_id}-campaign-copy.md"'},
    )


@app.post("/api/cron/refresh-exclusion-cache")
def refresh_exclusion_cache():
    """Called on a schedule by Vercel Cron (see vercel.json) once deployed.
    Not tied to any single run -- refreshes the shared exclusion cache that
    every run's Step 3 reads from. Does as much work as fits in one
    invocation's time budget and reports whether a full pass completed;
    Cron calling this repeatedly makes incremental progress either way.
    No-ops with a clear reason if Redis isn't configured (local dev) --
    local dev keeps using the local CSV file directly, nothing to refresh."""
    if not HUBSPOT_API_KEY:
        raise HTTPException(400, "HUBSPOT_API_KEY is not set -- cannot refresh the exclusion cache.")
    try:
        return exclusion_cache_refresh.refresh(HUBSPOT_API_KEY)
    except RuntimeError as exc:
        return {"skipped": True, "reason": str(exc)}


def _get_run_or_404(run_id):
    try:
        return runs.get_run(run_id)
    except KeyError:
        raise HTTPException(404, "unknown run_id")


def _require_step(run, step_name):
    if step_name not in run.step_results:
        raise HTTPException(400, f"{step_name} has not run yet for this run")
