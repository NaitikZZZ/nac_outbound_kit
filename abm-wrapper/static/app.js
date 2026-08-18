let runId = null;
const ROW_RENDER_CAP = 2000;

async function ensureRun() {
  if (runId) return runId;
  const resp = await fetch("/api/runs", { method: "POST" });
  const data = await resp.json();
  runId = data.run_id;
  document.getElementById("topbar-runid").textContent = runId;
  document.getElementById("topbar-status").textContent = "Run in progress";
  return runId;
}

document.getElementById("btn-copy-runid").addEventListener("click", () => {
  if (!runId) return;
  navigator.clipboard.writeText(runId);
  const btn = document.getElementById("btn-copy-runid");
  const original = btn.textContent;
  btn.textContent = "Copied";
  setTimeout(() => (btn.textContent = original), 1200);
});

// Wraps a button's click handler with a disabled/"Working…" state so slow
// steps (e.g. resolving domains for a large real list) don't look stuck, and
// surfaces exactly how long that step took in the top bar.
function withBusy(button, fn) {
  button.addEventListener("click", async () => {
    const original = button.textContent;
    button.disabled = true;
    button.textContent = "Working…";
    const start = performance.now();
    try {
      await fn();
    } catch (err) {
      console.error(err);
      alert("Something went wrong: " + err.message);
    } finally {
      button.disabled = false;
      button.textContent = original;
      const seconds = ((performance.now() - start) / 1000).toFixed(1);
      document.getElementById("topbar-last-action").textContent = `Last step: ${seconds}s`;
    }
  });
}

// Reveals a card and scrolls it into view -- without this, a newly-appeared
// section below the fold looks identical to nothing having happened.
function showCard(id) {
  const el = document.getElementById(id);
  el.style.display = "block";
  requestAnimationFrame(() => el.scrollIntoView({ behavior: "smooth", block: "start" }));
}

function setActiveStep(n) {
  document.querySelectorAll("#step-list li").forEach((li) => {
    li.classList.toggle("active", Number(li.dataset.step) === n);
  });
}

function pct(x) {
  return `${Math.round(x * 100)}%`;
}

async function refreshLog() {
  if (!runId) return;
  const resp = await fetch(`/api/runs/${runId}/state`);
  const data = await resp.json();
  const el = document.getElementById("log-entries");
  el.innerHTML = data.log
    .map(
      (e) =>
        `<div class="log-entry"><span class="log-time">${e.ts}</span>${e.message} <span class="log-dur">(${e.duration_ms}ms)</span></div>`,
    )
    .join("");
  el.scrollTop = el.scrollHeight;
}

// Full scrollable table — every column, every row (capped for sanity on huge lists).
function renderFullTable(headers, rows) {
  if (!rows || !rows.length) return "<p>No rows.</p>";
  const shown = rows.slice(0, ROW_RENDER_CAP);
  let html = '<div class="table-scroll"><table><thead><tr>';
  html += headers.map((h) => `<th>${h}</th>`).join("");
  html += "</tr></thead><tbody>";
  for (const row of shown) {
    html += "<tr>" + headers.map((h) => `<td title="${(row[h] || "").toString().replace(/"/g, "&quot;")}">${(row[h] || "").toString()}</td>`).join("") + "</tr>";
  }
  html += "</tbody></table></div>";
  if (rows.length > ROW_RENDER_CAP) {
    html += `<p class="table-caption">Showing first ${ROW_RENDER_CAP} of ${rows.length} rows. Download the CSV for the full set.</p>`;
  }
  return html;
}

async function renderTrackInto(track, containerId) {
  const resp = await fetch(`/api/runs/${runId}/rows/${track}`);
  const data = await resp.json();
  document.getElementById(containerId).innerHTML = renderFullTable(data.headers, data.rows);
}

withBusy(document.getElementById("btn-upload"), async () => {
  const fileInput = document.getElementById("file-input");
  if (!fileInput.files.length) return alert("Choose a CSV first.");
  await ensureRun();

  const form = new FormData();
  form.append("file", fileInput.files[0]);
  const resp = await fetch(`/api/runs/${runId}/upload`, { method: "POST", body: form });
  if (!resp.ok) return alert("Upload failed: " + (await resp.text()));
  const data = await resp.json();

  document.getElementById("result-step1").innerHTML = `
    <span class="pill">${data.row_count} rows</span>
    <span class="pill">domain filled ${pct(data.domain_fill_rate)}</span>
    <span class="pill">email filled ${pct(data.email_fill_rate)}</span>
    <div id="result-step1-table"></div>
  `;
  await renderTrackInto("ok", "result-step1-table");
  showCard("card-domain");
  setActiveStep(2);
  refreshLog();
});

// Renders Step 2's result pills + table, and -- if this run used Clearbit
// only and some companies still came back unresolved -- a follow-up button
// to send just those through Claude + web search. Re-running the same
// endpoint is safe and cheap for the already-resolved rows: they hit the
// local domain cache instantly, so only the genuinely unresolved ones incur
// a real Clearbit retry + Claude lookup.
async function renderDomainResult(data) {
  const el = document.getElementById("result-step2");
  if (data.skipped) {
    el.innerHTML = `<p>Skipped — ${data.reason}</p>`;
    return;
  }
  el.innerHTML = `
    <span class="pill">${data.newly_resolved} newly resolved</span>
    <span class="pill">cache ${data.by_source.cache}</span>
    <span class="pill">clearbit ${data.by_source.clearbit}</span>
    <span class="pill">claude ${data.by_source.claude}</span>
    <span class="pill">apollo ${data.by_source.apollo}</span>
    <span class="pill">unresolved ${data.by_source.unresolved}</span>
    <div id="domain-claude-fallback"></div>
    <div id="result-step2-table"></div>`;
  await renderTrackInto("ok", "result-step2-table");

  const fallbackEl = document.getElementById("domain-claude-fallback");
  if (!data.used_ai_fallback && data.by_source.unresolved > 0) {
    const n = data.by_source.unresolved;
    fallbackEl.innerHTML = `<p class="hint">${n} compan${n === 1 ? "y" : "ies"} still unresolved after Clearbit.
      <button id="btn-resolve-unresolved-claude" class="secondary">Try Claude + web search for these (~$0.01-0.02 each)</button></p>`;
    withBusy(document.getElementById("btn-resolve-unresolved-claude"), async () => {
      const retryForm = new FormData();
      retryForm.append("run_step", "true");
      retryForm.append("use_ai_fallback", "true");
      const retryResp = await fetch(`/api/runs/${runId}/steps/domain-resolution`, { method: "POST", body: retryForm });
      const retryData = await retryResp.json();
      await renderDomainResult(retryData);
      refreshLog();
    });
  } else if (data.used_ai_fallback && !data.used_apollo_fallback && data.by_source.unresolved > 0) {
    const n = data.by_source.unresolved;
    fallbackEl.innerHTML = `<p class="hint">${n} compan${n === 1 ? "y" : "ies"} still unresolved after Claude.
      <button id="btn-resolve-unresolved-apollo" class="secondary">Try Apollo org search for these (costs 1 Apollo credit each)</button></p>`;
    withBusy(document.getElementById("btn-resolve-unresolved-apollo"), async () => {
      const retryForm = new FormData();
      retryForm.append("run_step", "true");
      retryForm.append("use_ai_fallback", "true");
      retryForm.append("use_apollo_fallback", "true");
      const retryResp = await fetch(`/api/runs/${runId}/steps/domain-resolution`, { method: "POST", body: retryForm });
      const retryData = await retryResp.json();
      await renderDomainResult(retryData);
      refreshLog();
    });
  }
}

withBusy(document.getElementById("btn-domain"), async () => {
  const form = new FormData();
  form.append("run_step", document.getElementById("chk-run-domain").checked);
  form.append("use_ai_fallback", document.getElementById("chk-ai-fallback").checked);
  const resp = await fetch(`/api/runs/${runId}/steps/domain-resolution`, { method: "POST", body: form });
  const data = await resp.json();
  await renderDomainResult(data);
  await loadTitleChecklist();
  showCard("card-titles");
  setActiveStep(3);
  refreshLog();
});

function titleRowHtml(t) {
  const checked = t.default_excluded ? "checked" : "";
  return `<label data-title-search="${t.title.toLowerCase()}"><input type="checkbox" class="title-check" value="${t.title.replace(/"/g, "&quot;")}" ${checked} /> ${t.title} <span class="title-count">${t.count}</span></label>`;
}

async function loadTitleChecklist() {
  const resp = await fetch(`/api/runs/${runId}/titles`);
  const data = await resp.json();
  const el = document.getElementById("title-checklist");
  if (!data.titles.length) {
    el.innerHTML = "<em>No title column detected — nothing to filter here.</em>";
    return;
  }
  const defaults = data.titles.filter((t) => t.default_excluded);
  const others = data.titles.filter((t) => !t.default_excluded);

  let html = "";
  if (defaults.length) {
    html += `<div class="title-group-label">Excluded by default (Intern / Student / Retired)</div>`;
    html += defaults.map(titleRowHtml).join("");
    html += `<div class="title-group-label">Other titles</div>`;
  }
  html += others.length ? others.map(titleRowHtml).join("") : "<em>No other titles.</em>";
  el.innerHTML = html;
}

document.getElementById("title-search").addEventListener("input", (e) => {
  const q = e.target.value.trim().toLowerCase();
  document.querySelectorAll("#title-checklist label[data-title-search]").forEach((label) => {
    label.style.display = label.dataset.titleSearch.includes(q) ? "flex" : "none";
  });
});

withBusy(document.getElementById("btn-title-exclusion"), async () => {
  const checked = Array.from(document.querySelectorAll(".title-check:checked")).map((c) => c.value);
  const form = new FormData();
  checked.forEach((t) => form.append("excluded_titles", t));
  const resp = await fetch(`/api/runs/${runId}/steps/title-exclusion`, { method: "POST", body: form });
  const data = await resp.json();
  document.getElementById("result-titles").innerHTML = `<span class="pill">${data.excluded_count} excluded by title</span><span class="pill">${data.remaining_ok} remain</span>`;
  showCard("card-exclusion");
  setActiveStep(3);
  refreshLog();
});

withBusy(document.getElementById("btn-exclusion"), async () => {
  const runCheck = document.getElementById("chk-run-exclusion").checked;
  const form = new FormData();
  form.append("run_check", runCheck);
  const resp = await fetch(`/api/runs/${runId}/steps/exclusion-check`, { method: "POST", body: form });
  const data = await resp.json();
  document.getElementById("result-step3").innerHTML = data.ran
    ? `<span class="pill">${data.ok_count} OK</span><span class="pill">${data.excluded_count} excluded</span>`
    : `<p>Skipped by user choice — all ${data.ok_count} rows treated as OK.</p>`;

  document.getElementById("exclusion-workspace").style.display = "flex";
  document.getElementById("ok-count").textContent = data.ok_count;
  document.getElementById("excluded-count").textContent = data.excluded_count;
  await renderTrackInto("ok", "ok-table");
  await renderTrackInto("excluded", "excluded-table");

  await loadTaxonomy();
  showCard("card-people");
  document.getElementById("card-downloads").style.display = "block";
  document.getElementById("dl-ok").href = `/api/runs/${runId}/download/ok`;
  document.getElementById("dl-excluded").href = `/api/runs/${runId}/download/excluded`;
  setActiveStep(4);
  refreshLog();
});

async function loadTaxonomy() {
  const resp = await fetch(`/api/runs/${runId}/apollo-taxonomy`);
  const data = await resp.json();

  const senEl = document.getElementById("seniorities");
  senEl.innerHTML = data.seniorities.map((s) => `<option value="${s}">${s.replace(/_/g, " ")}</option>`).join("");

  const empEl = document.getElementById("employee-range");
  empEl.innerHTML =
    '<option value="">Any</option>' +
    data.employee_buckets.map(([value, label]) => `<option value="${value}">${label}</option>`).join("");

  document.getElementById("regions").value = data.default_regions.slice(0, 5).join(", ");
  document.getElementById("titles").value = "";
  document.getElementById("titles").placeholder = data.default_titles.slice(0, 8).join(", ") + " ...";
}

document.getElementById("chk-run-people").addEventListener("change", (e) => {
  document.getElementById("people-options").style.display = e.target.checked ? "block" : "none";
});

withBusy(document.getElementById("btn-people"), async () => {
  const form = new FormData();
  const runPeople = document.getElementById("chk-run-people").checked;
  form.append("run_step", runPeople);
  form.append("work_email_only", document.getElementById("email-policy").value === "work_only");
  Array.from(document.getElementById("seniorities").selectedOptions).forEach((o) => form.append("seniorities", o.value));
  form.append("employee_range", document.getElementById("employee-range").value);
  form.append("regions", document.getElementById("regions").value);
  form.append("titles", document.getElementById("titles").value);

  const resp = await fetch(`/api/runs/${runId}/steps/people-discovery`, { method: "POST", body: form });
  const data = await resp.json();
  if (data.skipped) {
    document.getElementById("result-step4").innerHTML = `<p>Skipped — ${data.reason}</p>`;
  } else {
    document.getElementById("result-step4").innerHTML = `
      <span class="pill">${data.counts.discovered} discovered</span>
      <span class="pill">${data.counts.personal_email_needs_reveal} personal-email identified</span>
      <span class="pill">${data.counts.excluded_personal_only} excluded (personal-only policy)</span>
      <span class="pill">${data.counts.not_found} not found</span>
      <p class="hint">${data.note}</p>
      <div id="result-step4-table"></div>`;
    await renderTrackInto("ok", "result-step4-table");
  }
  document.getElementById("dl-ok").href = `/api/runs/${runId}/download/ok`;
  document.getElementById("dl-excluded").href = `/api/runs/${runId}/download/excluded`;

  const estResp = await fetch(`/api/runs/${runId}/steps/email-reveal/estimate`);
  const est = await estResp.json();
  document.getElementById("email-reveal-estimate").textContent =
    `${est.rows_needing_reveal} row(s) need a reveal. Spends real Apollo credits: 1 per person found (0 if not). Unchecked by default.`;
  showCard("card-email-reveal");
  setActiveStep(5);
  refreshLog();
});

withBusy(document.getElementById("btn-email-reveal"), async () => {
  const form = new FormData();
  form.append("run_step", document.getElementById("chk-run-email-reveal").checked);
  const resp = await fetch(`/api/runs/${runId}/steps/email-reveal`, { method: "POST", body: form });
  const data = await resp.json();
  document.getElementById("result-step5").innerHTML = data.skipped
    ? `<p>Skipped — ${data.reason}</p>`
    : `<span class="pill">${data.counts.revealed} revealed</span><span class="pill">${data.counts.already_had_email} already had one</span><span class="pill">${data.counts.not_found} not found</span>`;
  showCard("card-phone-reveal");
  setActiveStep(6);
  refreshLog();
});

withBusy(document.getElementById("btn-phone-reveal"), async () => {
  const form = new FormData();
  form.append("run_step", document.getElementById("chk-run-phone-reveal").checked);
  const resp = await fetch(`/api/runs/${runId}/steps/phone-reveal`, { method: "POST", body: form });
  const data = await resp.json();
  document.getElementById("result-step6").innerHTML = data.skipped
    ? `<p>Skipped — ${data.reason}</p>`
    : `<p class="hint">${data.note || ""}</p><span class="pill">${data.attempted || 0} attempted</span><span class="pill">${data.pending || 0} pending</span>`;

  const optResp = await fetch(`/api/runs/${runId}/naming-options`);
  const opts = await optResp.json();
  const fill = (id, values) => {
    document.getElementById(id).innerHTML = values.map((v) => `<option value="${v}">${v}</option>`).join("");
  };
  fill("name-priority", opts.priority);
  fill("name-team", opts.team);
  fill("name-usecase", opts.use_case);
  fill("name-region", opts.region);
  fill("name-channel", opts.channel);

  showCard("card-output-files");
  setActiveStep(7);
  refreshLog();
});

withBusy(document.getElementById("btn-output-files"), async () => {
  const form = new FormData();
  form.append("priority", document.getElementById("name-priority").value);
  form.append("team", document.getElementById("name-team").value);
  form.append("use_case", document.getElementById("name-usecase").value);
  form.append("region", document.getElementById("name-region").value);
  form.append("channel", document.getElementById("name-channel").value);
  form.append("poc_name", document.getElementById("name-poc").value);
  form.append("start_date", document.getElementById("name-startdate").value);

  const resp = await fetch(`/api/runs/${runId}/steps/output-files`, { method: "POST", body: form });
  const data = await resp.json();
  document.getElementById("result-step7").innerHTML = `
    <span class="pill">Campaign: ${data.campaign_name}</span>
    <span class="pill">email file: ${data.counts.email}</span>
    <span class="pill">LinkedIn file: ${data.counts.linkedin}</span>
    <span class="pill">calling file: ${data.counts.calling}</span>`;

  if (data.counts.linkedin > 0) {
    document.getElementById("heyreach-confirm-text").textContent =
      `This will create a new HeyReach list named "${data.campaign_name}" and add ${data.counts.linkedin} lead(s) to it. This writes to your live HeyReach account.`;
    document.getElementById("heyreach-confirm").style.display = "block";
  } else {
    showCard("card-associations");
    await loadAssociations();
    setActiveStep(8);
  }
  refreshLog();
});

withBusy(document.getElementById("btn-push-heyreach"), async () => {
  const form = new FormData();
  form.append("confirm", "true");
  const resp = await fetch(`/api/runs/${runId}/steps/output-files/push-heyreach`, { method: "POST", body: form });
  const data = await resp.json();
  document.getElementById("result-heyreach").innerHTML = data.error
    ? `<p>${data.error}</p>`
    : `<span class="pill">list ID: ${data.list_id}</span><span class="pill">${data.added} added</span><span class="pill">${data.failed} failed</span>`;
  showCard("card-associations");
  await loadAssociations();
  setActiveStep(8);
  refreshLog();
});

async function loadAssociations() {
  const resp = await fetch(`/api/runs/${runId}/steps/associations`);
  const data = await resp.json();
  const fill = (id, records) => {
    document.getElementById(id).innerHTML =
      '<option value="">None</option>' + records.map((r) => `<option value="${r.id}">${r.name}</option>`).join("");
  };
  fill("assoc-project", data.projects);
  fill("assoc-partner", data.partners);
  fill("assoc-event", data.events);
}

document.getElementById("chk-skip-associations").addEventListener("change", (e) => {
  document.getElementById("association-pickers").style.display = e.target.checked ? "none" : "block";
});

function currentAssociation() {
  if (document.getElementById("chk-skip-associations").checked) return null;
  const pick = (selectId, type) => {
    const val = document.getElementById(selectId).value;
    return val ? { object_type: type, object_id: val } : null;
  };
  return (
    pick("assoc-project", "0-970") || pick("assoc-partner", "p6512810_partners") || pick("assoc-event", "p6512810_events")
  );
}

withBusy(document.getElementById("btn-associations"), async () => {
  showCard("card-upload-ok");
  const previewForm = new FormData();
  previewForm.append("track", "ok");
  const resp = await fetch(`/api/runs/${runId}/steps/upload/preview`, { method: "POST", body: previewForm });
  const data = await resp.json();
  document.getElementById("result-upload-ok-preview").innerHTML =
    `<span class="pill">Campaign: ${data.campaign_name}</span><span class="pill">${data.contact_count} contact(s) will be uploaded</span>`;
  setActiveStep(9);
  refreshLog();
});

withBusy(document.getElementById("btn-upload-ok"), async () => {
  const assoc = currentAssociation();
  const form = new FormData();
  form.append("track", "ok");
  form.append("confirm", "true");
  if (assoc) {
    form.append("association_object_type", assoc.object_type);
    form.append("association_object_id", assoc.object_id);
  }
  const resp = await fetch(`/api/runs/${runId}/steps/upload/execute`, { method: "POST", body: form });
  const data = await resp.json();
  document.getElementById("result-upload-ok").innerHTML =
    `<span class="pill">${data.upserted_count || 0} upserted</span><span class="pill">list: ${data.list_id || "n/a"}</span><span class="pill">associated: ${data.associated}</span>`;

  showCard("card-upload-farming");
  const previewForm = new FormData();
  previewForm.append("track", "farming");
  const pResp = await fetch(`/api/runs/${runId}/steps/upload/preview`, { method: "POST", body: previewForm });
  const pData = await pResp.json();
  document.getElementById("result-upload-farming-preview").innerHTML =
    `<span class="pill">Campaign: ${pData.campaign_name}</span><span class="pill">${pData.contact_count} contact(s) will be uploaded</span>`;
  refreshLog();
});

withBusy(document.getElementById("btn-upload-farming"), async () => {
  const form = new FormData();
  form.append("track", "farming");
  form.append("confirm", "true");
  const resp = await fetch(`/api/runs/${runId}/steps/upload/execute`, { method: "POST", body: form });
  const data = await resp.json();
  document.getElementById("result-upload-farming").innerHTML =
    `<span class="pill">${data.upserted_count || 0} upserted</span><span class="pill">list: ${data.list_id || "n/a"}</span>`;

  const estResp = await fetch(`/api/runs/${runId}/steps/copy-agent/estimate`);
  const est = await estResp.json();
  const segLines = est.segments.map((s) => `${s.label}: ${s.lead_count}`).join(", ") || "no segments matched";
  document.getElementById("copy-agent-hint").textContent = est.anthropic_key_set
    ? `Would segment into: ${segLines}${est.dropped_segment_count ? ` (+${est.dropped_segment_count} smaller segment(s) not generated)` : ""}.`
    : "ANTHROPIC_API_KEY is not set -- Copy Agent will be skipped if you run this step.";
  showCard("card-copy-agent");
  setActiveStep(10);
  refreshLog();
});

withBusy(document.getElementById("btn-copy-agent"), async () => {
  const form = new FormData();
  form.append("run_step", document.getElementById("chk-run-copy-agent").checked);
  const resp = await fetch(`/api/runs/${runId}/steps/copy-agent`, { method: "POST", body: form });
  const data = await resp.json();

  if (data.skipped) {
    document.getElementById("result-step10").innerHTML = `<p>Skipped — ${data.reason}</p>`;
    document.getElementById("copy-agent-segments").innerHTML = "";
    refreshLog();
    return;
  }

  const totalCovered = data.segments.reduce((sum, s) => sum + s.lead_count, 0);
  document.getElementById("result-step10").innerHTML = `
    <span class="pill">${data.segments.length} segment(s)</span>
    <span class="pill">${totalCovered} of ${data.total_leads} lead(s) covered</span>
    ${data.dropped_segment_count ? `<span class="pill">${data.dropped_segment_count} smaller segment(s) skipped</span>` : ""}
    <a href="/api/runs/${runId}/steps/copy-agent/download">Download campaign copy (Markdown)</a>`;

  document.getElementById("copy-agent-segments").innerHTML = data.segments
    .map((seg) => {
      if (!seg.copy) {
        return `<div class="copy-segment"><h3>${seg.label} (${seg.lead_count})</h3><p class="hint">Failed: ${seg.error || "unknown error"}</p></div>`;
      }
      const c = seg.copy;
      return `<div class="copy-segment">
        <h3>${seg.label} (${seg.lead_count} lead(s), ${seg.role})</h3>
        <p class="hint"><strong>Email 1 subject:</strong> ${c.email_subject}</p>
        <pre>${c.email_body}</pre>
        <p class="hint"><strong>Follow-up subject:</strong> ${c.email_followup_subject}</p>
        <pre>${c.email_followup_body}</pre>
        <p class="hint"><strong>LinkedIn connect note:</strong></p>
        <pre>${c.linkedin_connect_note}</pre>
        <p class="hint"><strong>LinkedIn follow-up DM:</strong></p>
        <pre>${c.linkedin_followup_dm}</pre>
      </div>`;
    })
    .join("");
  refreshLog();
});
