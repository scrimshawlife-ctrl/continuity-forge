/**
 * Continuity Forge — creative production workspace
 * Default journey: Project → Import → Analyze Script → Scenes / Continuity →
 * Generate/Export → Review. Engineering controls live under Settings → Developer.
 * Display actions never mutate film canon.
 */

const SAMPLE_SCRIPT = `Title: Continuity Sample
Author: Continuity Forge
Episode: 1

# ACT ONE
= Setup — red keycard and clean jacket

INT. SAFEHOUSE - NIGHT

Mara enters through the rear door, jacket unbloodied, red keycard clipped at her belt.
She sets a brass compass on the table.

MARA
If the jacket changes, the timeline is lying.

ELI
(checking the monitor)
Then lock the prop before we cut.

Mara pockets the compass and exits toward the alley.

CUT TO:

INT. ALLEY - CONTINUOUS

Mara still wears the unbloodied jacket. The red keycard remains at her belt.
A blade glances her left forearm — a thin cut only.

MARA
Keep rolling. Do not rewrite the wound.

DISSOLVE TO:

INT. SAFEHOUSE - LATER

FLASHBACK - THE SAME TABLE, HOURS EARLIER

Mara places the brass compass beside an unopened envelope.
The jacket is clean. No keycard yet.

MARA
This is the plant.

BACK TO PRESENT

Mara re-enters. Jacket now torn at the left sleeve; the forearm cut is visible and slightly deeper.
The red keycard is gone. The brass compass is back on the table — payoff.

ELI
State drift. The keycard vanished between alley and return.

MARA
Then the ledger was never canonical.
`;

const STORAGE_KEY = "cf.product.projects.v1";
const LAST_KEY = "cf.product.lastProject";

const ANALYSIS_STAGES = [
  "Reading screenplay",
  "Detecting scenes",
  "Extracting characters and locations",
  "Building continuity timeline",
  "Preparing shot suggestions",
  "Checking for conflicts",
];

const $ = (id) => document.getElementById(id);

/** @typedef {{
 *  document_key: string,
 *  title: string,
 *  production_type: string,
 *  format: string,
 *  text: string,
 *  phase: string,
 *  summary: object|null,
 *  scenes: object[],
 *  entities: object[],
 *  breakdown: object|null,
 *  sceneDetail: object|null,
 *  scenePackage: object|null,
 *  overrides: object[],
 *  resolvedConflictIds: string[],
 *  reviewDecisions: object[],
 *  updatedAt: string
 * }} Project */

/** @type {Project|null} */
let current = null;
/** @type {Record<string, Project>} */
let projects = {};
/** @type {string} */
let activeView = "projects";
/** @type {string|null} */
let selectedSceneId = null;
/** @type {string} */
let continuityTab = "characters";
/** @type {object|null} */
let pendingOverride = null;

// --- Storage (local durable for product path; server store via ingest when used) ---

function loadProjects() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    projects = raw ? JSON.parse(raw) : {};
  } catch {
    projects = {};
  }
}

function saveProjects() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(projects));
    if (current) localStorage.setItem(LAST_KEY, current.document_key);
  } catch {
    /* ignore quota */
  }
}

function baseUrl() {
  const el = $("api-base");
  const v = el && el.value.trim();
  return v ? v.replace(/\/$/, "") : "";
}

async function api(path, options = {}) {
  const url = `${baseUrl()}${path}`;
  const headers = {
    "Content-Type": "application/json",
    Accept: "application/json",
    ...(options.headers || {}),
  };
  const res = await fetch(url, { ...options, headers });
  const text = await res.text();
  let body = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  if (!res.ok) {
    const err = new Error(
      (body && body.detail && (body.detail.what_happened || body.detail.title || JSON.stringify(body.detail))) ||
        body?.detail ||
        res.statusText ||
        "Request failed"
    );
    err.status = res.status;
    err.detail = body?.detail ?? body;
    throw err;
  }
  return body;
}

function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function showAlert(message, { kind = "error", technical = "" } = {}) {
  const el = $("alert");
  if (!el) return;
  el.hidden = false;
  el.className = `alert alert--${kind === "ok" ? "ok" : "error"}`;
  let html = `<div>${escapeHtml(message)}</div>`;
  if (technical) {
    html += `<details><summary>Show technical details</summary><pre class="code-block">${escapeHtml(
      typeof technical === "string" ? technical : JSON.stringify(technical, null, 2)
    )}</pre></details>`;
  }
  el.innerHTML = html;
}

function clearAlert() {
  const el = $("alert");
  if (el) {
    el.hidden = true;
    el.innerHTML = "";
  }
}

function detectFormat(filename, text) {
  const name = (filename || "").toLowerCase();
  if (name.endsWith(".fdx") || /^\s*<\?xml/.test(text) || text.slice(0, 500).includes("<FinalDraft")) {
    return "fdx";
  }
  return "fountain";
}

function setFormatLabels(fmt) {
  const label = fmt === "fdx" ? "FDX" : "Fountain";
  ["format-label", "format-label-active"].forEach((id) => {
    const el = $(id);
    if (el) el.textContent = label;
  });
}

// --- UI shell ---

function setView(view) {
  activeView = view;
  document.querySelectorAll(".nav__item").forEach((btn) => {
    const v = btn.getAttribute("data-view");
    const on = v === view;
    btn.classList.toggle("is-active", on);
    if (on) btn.setAttribute("aria-current", "page");
    else btn.removeAttribute("aria-current");
  });
  document.querySelectorAll("[data-view-panel]").forEach((panel) => {
    panel.hidden = panel.getAttribute("data-view-panel") !== view;
  });
  updateStickyCta();
  if (view === "scenes") renderScenes();
  if (view === "continuity") renderContinuity();
  if (view === "generate") renderGenerate();
  if (view === "review") renderReview();
  if (view === "export") {
    /* static buttons */
  }
}

function enableWorkflowNav(enabled) {
  document.querySelectorAll(".nav__item").forEach((btn) => {
    const v = btn.getAttribute("data-view");
    if (v === "projects") {
      btn.disabled = false;
      return;
    }
    btn.disabled = !enabled;
  });
}

function updateProjectChrome() {
  const select = $("project-select");
  const titleEl = $("project-title");
  if (!select) return;
  const keys = Object.keys(projects).sort((a, b) =>
    (projects[b].updatedAt || "").localeCompare(projects[a].updatedAt || "")
  );
  select.innerHTML =
    `<option value="">No project</option>` +
    keys
      .map(
        (k) =>
          `<option value="${escapeHtml(k)}" ${
            current && current.document_key === k ? "selected" : ""
          }>${escapeHtml(projects[k].title || k)}</option>`
      )
      .join("");
  if (titleEl) titleEl.textContent = current ? current.title : "—";

  const recent = $("recent-projects");
  const list = $("recent-list");
  if (recent && list) {
    if (keys.length) {
      recent.hidden = false;
      list.innerHTML = keys
        .slice(0, 8)
        .map(
          (k) =>
            `<li><button type="button" class="btn btn--ghost btn--block" data-open-project="${escapeHtml(
              k
            )}">${escapeHtml(projects[k].title)} <span class="muted small">· ${escapeHtml(
              projects[k].phase || ""
            )}</span></button></li>`
        )
        .join("");
    } else {
      recent.hidden = true;
      list.innerHTML = "";
    }
  }
}

function showEmptyState() {
  $("empty-state").hidden = false;
  $("new-project-form").hidden = true;
  $("project-workspace").hidden = true;
  enableWorkflowNav(false);
  updateStickyCta();
}

function showNewProjectForm() {
  $("empty-state").hidden = true;
  $("new-project-form").hidden = false;
  $("project-workspace").hidden = true;
  if (!$("script").value.trim()) {
    /* keep empty for intentional create */
  }
}

function showProjectWorkspace() {
  $("empty-state").hidden = true;
  $("new-project-form").hidden = true;
  $("project-workspace").hidden = false;
  if (!current) return;
  $("active-title").textContent = current.title;
  $("production-type-label").textContent = current.production_type || "Production";
  $("phase-label").textContent = `Phase: ${humanPhase(current.phase)}`;
  $("script-active").value = current.text || "";
  setFormatLabels(current.format || "fountain");
  enableWorkflowNav(Boolean(current.breakdown || current.summary));
  if (current.summary) {
    renderAnalysisSummary(current.summary);
    $("analysis-summary").hidden = false;
  } else {
    $("analysis-summary").hidden = true;
  }
  $("analysis-progress").hidden = true;
  updateStickyCta();
  updateDevPanels();
}

function humanPhase(phase) {
  const map = {
    EMPTY: "Empty",
    IMPORTED: "Script imported",
    ANALYZING: "Analyzing",
    NEEDS_REVIEW: "Needs review",
    CONFLICTED: "Conflicts open",
    READY: "Ready",
    GENERATING: "Generating",
    REVIEWING: "Reviewing",
    APPROVED: "Approved",
    STALE: "Stale",
    ERROR: "Error",
  };
  return map[phase] || phase || "—";
}

function updateStickyCta() {
  const sticky = $("sticky-cta");
  if (!sticky) return;
  const show =
    current &&
    activeView === "projects" &&
    !$("project-workspace").hidden &&
    !$("analysis-progress").hidden === false
      ? false
      : current && activeView === "projects" && !$("project-workspace").hidden;
  sticky.classList.toggle("is-visible", Boolean(show));
  sticky.hidden = !show;
}

// --- Project create / open ---

async function createProjectFromForm(ev) {
  ev?.preventDefault?.();
  clearAlert();
  const title = ($("np-title").value || "").trim();
  const production_type = $("np-type").value;
  const text = $("script").value || "";
  if (!title) {
    showAlert("Please enter a project title.");
    return;
  }
  try {
    const created = await api("/v1/product/create-project", {
      method: "POST",
      body: JSON.stringify({
        title,
        production_type,
        text,
        format: detectFormat(null, text),
      }),
    });
    const project = {
      document_key: created.document_key,
      title: created.title,
      production_type: created.production_type,
      format: created.format,
      text,
      phase: created.phase,
      summary: null,
      scenes: [],
      entities: [],
      breakdown: null,
      sceneDetail: null,
      scenePackage: null,
      overrides: [],
      resolvedConflictIds: [],
      reviewDecisions: [],
      updatedAt: new Date().toISOString(),
    };
    projects[project.document_key] = project;
    current = project;
    saveProjects();
    updateProjectChrome();
    showProjectWorkspace();
    setView("projects");
    showAlert("Project created. Review the script, then Analyze Script.", { kind: "ok" });
  } catch (e) {
    showAlert(e.message || "Could not create project", { technical: e.detail || String(e) });
  }
}

function openProject(key) {
  const p = projects[key];
  if (!p) return;
  current = p;
  saveProjects();
  updateProjectChrome();
  showProjectWorkspace();
  setView("projects");
  if (p.summary) enableWorkflowNav(true);
}

// --- Import ---

function applyImportedText(text, filename) {
  const fmt = detectFormat(filename, text);
  setFormatLabels(fmt);
  if (current) {
    current.text = text;
    current.format = fmt;
    current.phase = "IMPORTED";
    current.summary = null;
    current.breakdown = null;
    current.scenes = [];
    current.updatedAt = new Date().toISOString();
    projects[current.document_key] = current;
    saveProjects();
    $("script-active").value = text;
    $("analysis-summary").hidden = true;
    enableWorkflowNav(false);
    showAlert(`Imported ${filename || "script"} · format ${fmt === "fdx" ? "FDX" : "Fountain"}. Click Analyze Script.`, {
      kind: "ok",
    });
  } else {
    $("script").value = text;
    showAlert(`Loaded ${filename || "script"}. Create the project to continue.`, { kind: "ok" });
  }
}

function handleFile(file) {
  if (!file) return;
  const name = file.name || "";
  const lower = name.toLowerCase();
  if (lower.endsWith(".pdf") || lower.endsWith(".docx") || lower.endsWith(".doc")) {
    showAlert("Unsupported file type. Use .fountain, .fdx, or .txt. PDF and DOCX are not supported yet.", {
      technical: name,
    });
    return;
  }
  const reader = new FileReader();
  reader.onload = () => applyImportedText(String(reader.result || ""), name);
  reader.onerror = () => showAlert("Could not read that file.");
  reader.readAsText(file);
}

// --- Analyze ---

function renderStages(activeIndex) {
  const ol = $("stage-list");
  if (!ol) return;
  ol.innerHTML = ANALYSIS_STAGES.map((label, i) => {
    let cls = "";
    if (i < activeIndex) cls = "is-done";
    if (i === activeIndex) cls = "is-current";
    return `<li class="${cls}">${escapeHtml(label)}</li>`;
  }).join("");
}

async function analyzeScript() {
  if (!current) {
    showAlert("Create or open a project first.");
    return;
  }
  clearAlert();
  const text = $("script-active").value || current.text || "";
  if (!text.trim()) {
    showAlert("Paste or import a screenplay before analyzing.", {
      technical: "empty script",
    });
    return;
  }
  current.text = text;
  current.format = detectFormat(null, text);
  current.phase = "ANALYZING";
  $("phase-label").textContent = `Phase: ${humanPhase(current.phase)}`;
  $("analysis-progress").hidden = false;
  $("analysis-summary").hidden = true;
  $("btn-analyze").disabled = true;
  $("btn-analyze-sticky").disabled = true;

  let stage = 0;
  renderStages(0);
  const timer = setInterval(() => {
    stage = Math.min(stage + 1, ANALYSIS_STAGES.length - 1);
    renderStages(stage);
  }, 450);

  try {
    const result = await api("/v1/product/analyze", {
      method: "POST",
      body: JSON.stringify({
        title: current.title,
        text,
        document_key: current.document_key,
        format: current.format,
        production_type: current.production_type,
        resolved_conflict_ids: current.resolvedConflictIds || [],
      }),
    });
    clearInterval(timer);
    renderStages(ANALYSIS_STAGES.length);
    current.summary = result.summary;
    current.scenes = result.scenes || [];
    current.entities = result.entities || [];
    current.breakdown = result.breakdown;
    current.phase = result.summary?.phase || "NEEDS_REVIEW";
    current.updatedAt = new Date().toISOString();
    projects[current.document_key] = current;
    saveProjects();
    $("analysis-progress").hidden = true;
    renderAnalysisSummary(result.summary);
    $("analysis-summary").hidden = false;
    $("phase-label").textContent = `Phase: ${humanPhase(current.phase)}`;
    enableWorkflowNav(true);
    updateDevPanels();
    showAlert("Script analysis complete. Review the breakdown when ready.", { kind: "ok" });
  } catch (e) {
    clearInterval(timer);
    $("analysis-progress").hidden = true;
    current.phase = "ERROR";
    $("phase-label").textContent = `Phase: ${humanPhase(current.phase)}`;
    const detail = e.detail;
    if (detail && typeof detail === "object" && detail.what_happened) {
      showAlert(
        `${detail.title || "Analysis error"}\n\n${detail.what_happened}\n\n${(detail.next_steps || []).join(" · ")}`,
        { technical: detail.technical_detail || detail }
      );
    } else {
      showAlert(e.message || "Analysis failed", { technical: detail || String(e) });
    }
  } finally {
    $("btn-analyze").disabled = false;
    $("btn-analyze-sticky").disabled = false;
    updateStickyCta();
  }
}

function renderAnalysisSummary(summary) {
  const grid = $("count-grid");
  if (!grid || !summary) return;
  const c = summary.counts || {};
  const items = [
    ["Scenes", c.scenes],
    ["Characters", c.characters],
    ["Locations", c.locations],
    ["Props", c.props],
    ["Shots", c.shots],
    ["Conflicts", c.conflicts],
  ];
  grid.innerHTML = items
    .map(
      ([k, v]) =>
        `<li><span>${escapeHtml(k)}</span><strong>${escapeHtml(String(v ?? 0))}</strong></li>`
    )
    .join("");
  const wrap = $("warning-list-wrap");
  const list = $("warning-list");
  const warnings = summary.warnings || [];
  if (warnings.length) {
    wrap.hidden = false;
    list.innerHTML = warnings.map((w) => `<li>${escapeHtml(w)}</li>`).join("");
  } else {
    wrap.hidden = true;
    list.innerHTML = "";
  }
}

// --- Scenes ---

function readinessBadge(r) {
  const label = r || "Needs Review";
  let cls = "badge--review";
  if (/conflict/i.test(label)) cls = "badge--conflict";
  if (/ready|approved|generated/i.test(label)) cls = "badge--ready";
  return `<span class="badge ${cls}" title="Scene readiness">${escapeHtml(label)}</span>`;
}

function renderScenes() {
  const host = $("scene-cards");
  const empty = $("scenes-empty");
  if (!host) return;
  if (!current?.scenes?.length) {
    host.innerHTML = "";
    if (empty) empty.hidden = false;
    $("scene-detail").hidden = true;
    return;
  }
  if (empty) empty.hidden = true;
  host.innerHTML = current.scenes
    .map((s) => {
      const selected = s.scene_id === selectedSceneId ? "is-selected" : "";
      return `<button type="button" class="scene-card ${selected}" data-scene-id="${escapeHtml(
        s.scene_id
      )}">
        <div class="scene-card__top">
          <span class="scene-card__num">Scene ${escapeHtml(String(s.scene_number))}</span>
          ${readinessBadge(s.readiness)}
        </div>
        <p class="scene-card__slug">${escapeHtml(s.slugline)}</p>
        <p class="scene-card__meta">
          ${escapeHtml((s.characters || []).slice(0, 3).join(", ") || "—")}
          · ${escapeHtml(String(s.shot_count))} shots
          ${s.warning_count ? ` · ${escapeHtml(String(s.warning_count))} warnings` : ""}
        </p>
      </button>`;
    })
    .join("");
  if (selectedSceneId) {
    loadSceneDetail(selectedSceneId);
  } else if (current.scenes[0]) {
    selectedSceneId = current.scenes[0].scene_id;
    loadSceneDetail(selectedSceneId);
  }
}

async function loadSceneDetail(sceneId) {
  if (!current) return;
  selectedSceneId = sceneId;
  document.querySelectorAll(".scene-card").forEach((el) => {
    el.classList.toggle("is-selected", el.getAttribute("data-scene-id") === sceneId);
  });
  try {
    const detail = await api(`/v1/product/scenes/${encodeURIComponent(sceneId)}`, {
      method: "POST",
      body: JSON.stringify({
        title: current.title,
        text: current.text,
        document_key: current.document_key,
        format: current.format,
        resolved_conflict_ids: current.resolvedConflictIds || [],
      }),
    });
    current.sceneDetail = detail;
    renderSceneDetail(detail);
  } catch (e) {
    showAlert(e.message || "Could not load scene", { technical: e.detail });
  }
}

function renderProv(v) {
  const p = v.provenance || {};
  return `<span class="prov" title="${escapeHtml(p.title || p.label || "")}">${escapeHtml(
    p.icon || ""
  )} ${escapeHtml(p.label || "INFERRED")}</span>`;
}

function renderSceneDetail(detail) {
  const panel = $("scene-detail");
  if (!panel || !detail) return;
  panel.hidden = false;
  const s = detail.scene || {};
  $("sd-status").textContent = s.readiness || "Needs Review";
  $("sd-title").textContent = `Scene ${s.scene_number}`;
  $("sd-slug").textContent = s.slugline || "";
  $("sd-excerpt").textContent = detail.script_excerpt || "(No excerpt matched in source text.)";
  $("sd-summary").textContent = s.summary || "No summary.";
  const ent = detail.entities_present || {};
  $("sd-entities").innerHTML = Object.entries(ent)
    .map(
      ([k, vals]) =>
        `<dt>${escapeHtml(k)}</dt><dd>${escapeHtml((vals || []).join(", ") || "—")}</dd>`
    )
    .join("");
  $("sd-entry").innerHTML = (detail.entry_state || [])
    .map(
      (v) =>
        `<li><strong>${escapeHtml(v.field_name)}</strong> ${escapeHtml(v.value)} ${renderProv(
          v
        )}</li>`
    )
    .join("");
  $("sd-exit").innerHTML = (detail.exit_state || [])
    .map(
      (v) =>
        `<li><strong>${escapeHtml(v.field_name)}</strong> ${escapeHtml(v.value)} ${renderProv(
          v
        )}</li>`
    )
    .join("");
  $("sd-shots").innerHTML = (detail.shots || [])
    .map(
      (sh) => `<article class="shot-card">
      <h4>Shot ${escapeHtml(sh.shot_number)} · ${escapeHtml(sh.shot_type)}</h4>
      <p>${escapeHtml(sh.description)}</p>
      <p>Characters: ${escapeHtml((sh.characters || []).join(", ") || "—")}</p>
      <p>Props: ${escapeHtml((sh.props || []).join(", ") || "—")}</p>
      <p class="muted small">Status: ${escapeHtml(sh.status || "DRAFT")}</p>
      <details>
        <summary>Prompt &amp; advanced</summary>
        <p>${escapeHtml(sh.prompt_preview || "")}</p>
        <p class="muted">Start hash: ${escapeHtml((sh.start_state_hash || "").slice(0, 12))}…</p>
      </details>
      <div class="shot-card__actions">
        <button type="button" class="btn btn--ghost btn--sm" data-copy-prompt="${escapeHtml(
          sh.shot_id
        )}">Copy Prompt</button>
        <button type="button" class="btn btn--ghost btn--sm" data-export-shot="${escapeHtml(
          sh.shot_id
        )}">Export</button>
      </div>
    </article>`
    )
    .join("") || "<p class='muted'>No proposed shots.</p>";

  const confWrap = $("sd-conflicts-wrap");
  const confHost = $("sd-conflicts");
  const conflicts = detail.conflicts || [];
  if (conflicts.length) {
    confWrap.hidden = false;
    confHost.innerHTML = conflicts.map(renderConflictCard).join("");
  } else {
    confWrap.hidden = true;
    confHost.innerHTML = "";
  }

  $("btn-scene-prev").disabled = !detail.prev_scene_id;
  $("btn-scene-next").disabled = !detail.next_scene_id;
  $("btn-prepare-scene").disabled = detail.blocking_conflict_count > 0;
  $("btn-prepare-scene").title =
    detail.blocking_conflict_count > 0
      ? "Resolve blocking conflicts before preparing this scene"
      : "Prepare Scene for Generation";
}

function renderConflictCard(c) {
  const choices = (c.choices || [])
    .map(
      (ch) =>
        `<button type="button" class="btn btn--ghost btn--sm" data-resolve="${escapeHtml(
          c.conflict_id
        )}" data-choice="${escapeHtml(ch.choice_id)}" ${c.resolved ? "disabled" : ""}>${escapeHtml(
          ch.label
        )}</button>`
    )
    .join("");
  return `<article class="conflict-card" data-conflict-id="${escapeHtml(c.conflict_id)}">
    <h4>${escapeHtml(c.category)} · ${escapeHtml(c.severity || "warning")}</h4>
    <p>${escapeHtml(c.plain_language)}</p>
    ${
      c.resolved
        ? `<p class="muted small">Resolved: ${escapeHtml(c.resolution_choice_id || "")}</p>`
        : `<div class="choices">${choices}</div>`
    }
    <details><summary>Technical details</summary><pre class="code-block">${escapeHtml(
      c.technical_detail || ""
    )}</pre></details>
  </article>`;
}

async function resolveConflictUi(conflictId, choiceId) {
  if (!current) return;
  const fromSummary = (current.summary?.conflicts || []).find((c) => c.conflict_id === conflictId);
  const fromDetail = (current.sceneDetail?.conflicts || []).find((c) => c.conflict_id === conflictId);
  const conflict = fromSummary || fromDetail;
  if (!conflict) return;
  try {
    const res = await api("/v1/product/conflicts/resolve", {
      method: "POST",
      body: JSON.stringify({ conflict, choice_id: choiceId }),
    });
    current.resolvedConflictIds = Array.from(
      new Set([...(current.resolvedConflictIds || []), conflictId])
    );
    if (current.summary?.conflicts) {
      current.summary.conflicts = current.summary.conflicts.map((c) =>
        c.conflict_id === conflictId ? res.conflict : c
      );
    }
    saveProjects();
    showAlert("Conflict resolved. Re-analyze if you need updated readiness.", { kind: "ok" });
    if (selectedSceneId) await loadSceneDetail(selectedSceneId);
    if (activeView === "continuity") renderContinuity();
  } catch (e) {
    showAlert(e.message || "Could not resolve conflict", { technical: e.detail });
  }
}

// --- Continuity ---

function renderContinuity() {
  const host = $("continuity-panel");
  if (!host) return;
  document.querySelectorAll(".tabs__btn").forEach((btn) => {
    const on = btn.getAttribute("data-ctab") === continuityTab;
    btn.classList.toggle("is-active", on);
    btn.setAttribute("aria-selected", on ? "true" : "false");
  });
  if (!current?.entities?.length && !current?.summary) {
    host.innerHTML = "<p class='muted'>Analyze a script to open the continuity bible.</p>";
    return;
  }
  if (continuityTab === "conflicts") {
    const conflicts = current.summary?.conflicts || [];
    host.innerHTML = conflicts.length
      ? conflicts.map(renderConflictCard).join("")
      : "<p class='muted'>No open conflicts from analysis.</p>";
    return;
  }
  if (continuityTab === "timeline") {
    host.innerHTML = `<div class="entity-list">${(current.scenes || [])
      .map(
        (s) => `<article class="entity-card">
        <div class="entity-card__head">
          <strong>Scene ${escapeHtml(String(s.scene_number))}</strong>
          <span class="muted small">${escapeHtml(s.time_of_day || "—")}</span>
        </div>
        <p>${escapeHtml(s.slugline)}</p>
        <p class="muted small">Screenplay order · story chronology follows script (non-linear markers noted in analysis warnings when detected).</p>
      </article>`
      )
      .join("")}</div>`;
    return;
  }
  if (continuityTab === "relationships") {
    const links = current.breakdown?.setup_payoff_links || [];
    host.innerHTML = links.length
      ? `<div class="entity-list">${links
          .map(
            (l) => `<article class="entity-card">
          <strong>${escapeHtml(l.entity_name || l.entity_id)}</strong>
          <p class="muted small">Setup → payoff relationship (from continuity analysis)</p>
        </article>`
          )
          .join("")}</div>`
      : "<p class='muted'>No setup/payoff relationships extracted.</p>";
    return;
  }
  const kindMap = {
    characters: "character",
    locations: "location",
    wardrobe: "wardrobe",
    props: "prop",
  };
  const kind = kindMap[continuityTab];
  let entities = (current.entities || []).filter((e) => e.kind === kind);
  if (continuityTab === "wardrobe" && !entities.length) {
    host.innerHTML =
      "<p class='muted'>No wardrobe entities extracted yet. Wardrobe is tracked when the script provides wearables; lock values after review.</p>";
    return;
  }
  host.innerHTML = `<div class="entity-list">${entities
    .map((e) => {
      const values = (e.values || [])
        .map(
          (v) =>
            `<li><strong>${escapeHtml(v.field_name)}</strong> ${escapeHtml(v.value)} ${renderProv(
              v
            )}
            <button type="button" class="btn btn--ghost btn--sm" data-lock-entity="${escapeHtml(
              e.entity_id
            )}" data-field="${escapeHtml(v.field_name)}" data-original="${escapeHtml(
              v.value
            )}">Lock edit…</button></li>`
        )
        .join("");
      return `<article class="entity-card">
        <div class="entity-card__head">
          <strong>${escapeHtml(e.name)}</strong>
          <span class="badge">${escapeHtml(e.kind)}</span>
        </div>
        <p class="muted small">Scenes: ${(e.scene_ordinals || []).join(", ") || "—"}
          · first ${escapeHtml(String(e.first_scene_ordinal ?? "—"))}
          · last ${escapeHtml(String(e.last_scene_ordinal ?? "—"))}</p>
        <ul class="value-list">${values}</ul>
      </article>`;
    })
    .join("")}</div>`;
}

async function lockEntityValue(entityId, field, original) {
  if (!current) return;
  const locked = window.prompt(`Lock new value for ${field} (was: ${original})`, original);
  if (locked == null || locked === original) return;
  try {
    const res = await api("/v1/product/override/preview", {
      method: "POST",
      body: JSON.stringify({
        title: current.title,
        text: current.text,
        document_key: current.document_key,
        format: current.format,
        target_kind: "entity",
        target_id: entityId,
        field_name: field,
        original_value: original,
        locked_value: locked,
        rationale: "Operator lock from Continuity workspace",
      }),
    });
    pendingOverride = res;
    $("inv-message").textContent = res.invalidation?.message || "This change affects downstream work.";
    const inv = res.invalidation || {};
    $("inv-stats").innerHTML = [
      ["Scenes", inv.scene_count],
      ["Shots", inv.shot_count],
      ["Generated", inv.generated_candidate_count],
      ["Approved downstream", inv.approved_downstream_count],
    ]
      .map(
        ([k, v]) =>
          `<li class="stat"><span class="stat__k">${escapeHtml(k)}</span><span class="stat__v">${escapeHtml(
            String(v ?? 0)
          )}</span></li>`
      )
      .join("");
    $("invalidation-dialog").showModal();
  } catch (e) {
    showAlert(e.message || "Override preview failed", { technical: e.detail });
  }
}

function confirmOverride() {
  if (!current || !pendingOverride?.override) {
    $("invalidation-dialog").close();
    return;
  }
  current.overrides = [...(current.overrides || []), pendingOverride.override];
  current.phase = "STALE";
  current.updatedAt = new Date().toISOString();
  projects[current.document_key] = current;
  saveProjects();
  pendingOverride = null;
  $("invalidation-dialog").close();
  $("phase-label").textContent = `Phase: ${humanPhase(current.phase)}`;
  showAlert("Value locked (USER LOCKED). Original preserved. Dependents marked stale — re-analyze when ready.", {
    kind: "ok",
  });
  renderContinuity();
}

// --- Generate / prepare ---

async function prepareSelectedScene() {
  if (!current || !selectedSceneId) {
    showAlert("Select a scene first.");
    return;
  }
  try {
    const res = await api(`/v1/product/scenes/${encodeURIComponent(selectedSceneId)}/prepare`, {
      method: "POST",
      body: JSON.stringify({
        title: current.title,
        text: current.text,
        document_key: current.document_key,
        format: current.format,
        scene_id: selectedSceneId,
        warnings_acknowledged: true,
        resolved_conflict_ids: current.resolvedConflictIds || [],
      }),
    });
    current.scenePackage = res.package;
    saveProjects();
    setView("generate");
    renderGenerate();
    showAlert(
      res.message ||
        (res.provider_neutral
          ? "Scene package prepared (provider-neutral). Export anytime."
          : "Scene package prepared."),
      { kind: "ok" }
    );
  } catch (e) {
    showAlert(e.message || "Could not prepare scene", { technical: e.detail });
  }
}

function renderGenerate() {
  const pkg = current?.scenePackage;
  const panel = $("scene-package-panel");
  const missing = $("provider-missing");
  if (!pkg) {
    if (panel) panel.hidden = true;
    if (missing) missing.hidden = false;
    return;
  }
  if (missing) missing.hidden = false;
  if (panel) {
    panel.hidden = false;
    $("pkg-meta").textContent = `Scene ${pkg.scene_number} · ${pkg.slugline} · ${pkg.readiness} · hash ${String(
      pkg.package_hash || ""
    ).slice(0, 12)}…`;
    $("pkg-json").hidden = true;
    $("pkg-json").textContent = JSON.stringify(pkg, null, 2);
    $("gen-shot-cards").innerHTML = (pkg.shot_list || [])
      .map((s, i) => {
        const prompt = (pkg.shot_prompts || [])[i]?.prompt || "";
        return `<article class="shot-card">
          <h4>Shot ${escapeHtml(s.shot_number)}</h4>
          <p>${escapeHtml(s.description || "")}</p>
          <details open><summary>Prompt</summary><p>${escapeHtml(prompt)}</p></details>
          <div class="shot-card__actions">
            <button type="button" class="btn btn--ghost btn--sm" data-copy-text="${escapeHtml(
              prompt
            )}">Copy Prompt</button>
          </div>
        </article>`;
      })
      .join("");
  }
}

// --- Review ---

function renderReview() {
  const empty = $("review-empty");
  const list = $("review-list");
  const decisions = current?.reviewDecisions || [];
  if (!decisions.length) {
    empty.hidden = false;
    list.hidden = true;
    list.innerHTML = "";
    return;
  }
  empty.hidden = true;
  list.hidden = false;
  list.innerHTML = decisions
    .map(
      (d) => `<article class="card">
      <h3>${escapeHtml(d.action)} · shot ${escapeHtml(d.shot_id)}</h3>
      <p class="muted small">Lineage preserved · canon advances only via validated mutation paths (${
        d.advances_canon ? "intent to accept" : "no canon advance"
      })</p>
      ${d.note ? `<p>${escapeHtml(d.note)}</p>` : ""}
    </article>`
    )
    .join("");
}

async function recordReview(shotId, action) {
  if (!current) return;
  try {
    const res = await api("/v1/product/review/decision", {
      method: "POST",
      body: JSON.stringify({ shot_id: shotId, action, actor_id: "ui-operator" }),
    });
    current.reviewDecisions = [...(current.reviewDecisions || []), res.decision];
    saveProjects();
    showAlert(res.note || "Decision recorded.", { kind: "ok" });
    if (activeView === "review") renderReview();
  } catch (e) {
    showAlert(e.message || "Review decision failed", { technical: e.detail });
  }
}

// --- Export ---

function downloadText(filename, text, type = "text/plain") {
  const blob = new Blob([text], { type });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

function exportBreakdownJson() {
  if (!current?.breakdown) {
    showAlert("Analyze a script first.");
    return;
  }
  downloadText(
    `${current.document_key || "breakdown"}.breakdown.json`,
    JSON.stringify(current.breakdown, null, 2),
    "application/json"
  );
}

async function exportBreakdownMd() {
  if (!current) return;
  try {
    const res = await api("/v1/breakdown/markdown", {
      method: "POST",
      body: JSON.stringify({
        title: current.title,
        text: current.text,
        document_key: current.document_key,
        format: current.format,
      }),
    });
    downloadText(`${current.document_key || "breakdown"}.breakdown.md`, res.markdown || "");
  } catch (e) {
    showAlert(e.message || "Markdown export failed", { technical: e.detail });
  }
}

function exportShotListMd() {
  if (!current?.breakdown?.shots) {
    showAlert("Analyze a script first.");
    return;
  }
  const lines = [`# Shot list — ${current.title}`, ""];
  for (const s of current.breakdown.shots) {
    lines.push(`- **${s.scene_ordinal}.${s.shot_ordinal}** ${s.slugline} — ${s.label}`);
  }
  downloadText(`${current.document_key || "shots"}.shot-list.md`, lines.join("\n"));
}

function exportConflictReport() {
  const conflicts = current?.summary?.conflicts || [];
  const lines = [`# Conflict report — ${current?.title || ""}`, ""];
  if (!conflicts.length) lines.push("_No conflicts._");
  for (const c of conflicts) {
    lines.push(`## ${c.category} (${c.severity})`);
    lines.push(c.plain_language);
    lines.push(c.resolved ? `Resolved: ${c.resolution_choice_id}` : "Unresolved");
    lines.push("");
  }
  downloadText(`${current?.document_key || "conflicts"}.conflicts.md`, lines.join("\n"));
}

function exportScenePackage() {
  if (!current?.scenePackage) {
    showAlert("Prepare a scene for generation first (Scenes → Prepare Scene for Generation).");
    return;
  }
  downloadText(
    `${current.document_key || "scene"}.scene-package.json`,
    JSON.stringify(current.scenePackage, null, 2),
    "application/json"
  );
}

// --- Developer ---

function updateDevPanels() {
  const b = current?.breakdown;
  if (!b) {
    if ($("dev-hashes")) $("dev-hashes").textContent = "No analysis yet.";
    if ($("dev-raw-json")) $("dev-raw-json").textContent = "—";
    return;
  }
  $("dev-hashes").textContent = JSON.stringify(
    {
      package_hash: b.package_hash,
      source_hash: b.source_hash,
      production_ir_hash: b.production_ir_hash,
      ledger_hash: b.ledger_hash,
      shot_contracts_hash: b.shot_contracts_hash,
    },
    null,
    2
  );
  $("dev-raw-json").textContent = JSON.stringify(b, null, 2);
}

async function pingHealth() {
  try {
    const h = await api("/health");
    if ($("health-line")) {
      $("health-line").textContent = `Status: ${h.status} · backend ${h.backend} · v${h.version}`;
    }
  } catch {
    if ($("health-line")) $("health-line").textContent = "Status: unreachable";
  }
}

async function runMockProof() {
  if (!current?.text) {
    showAlert("Open a project with a script first.");
    return;
  }
  try {
    const receipt = await api("/v1/proof", {
      method: "POST",
      body: JSON.stringify({
        title: current.title,
        text: current.text,
        document_key: current.document_key,
        format: current.format,
        seed: 0,
        budget_seconds: 30,
      }),
    });
    const out = $("dev-proof-out");
    out.hidden = false;
    out.textContent = JSON.stringify(receipt, null, 2);
    showAlert("Mock pipeline test finished (not production film).", { kind: "ok" });
  } catch (e) {
    showAlert(e.message || "Mock proof failed", { technical: e.detail });
  }
}

// --- Events ---

function bindEvents() {
  document.querySelectorAll(".nav__item").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.disabled) return;
      setView(btn.getAttribute("data-view"));
    });
  });

  $("btn-new-project")?.addEventListener("click", showNewProjectForm);
  $("form-new-project")?.addEventListener("submit", createProjectFromForm);
  $("btn-create-project")?.addEventListener("click", createProjectFromForm);

  $("project-select")?.addEventListener("change", (e) => {
    const v = e.target.value;
    if (v) openProject(v);
    else {
      current = null;
      showEmptyState();
      updateProjectChrome();
    }
  });

  document.addEventListener("click", (e) => {
    const t = e.target.closest?.("[data-open-project]");
    if (t) openProject(t.getAttribute("data-open-project"));
    const sc = e.target.closest?.("[data-scene-id]");
    if (sc && sc.classList.contains("scene-card")) {
      loadSceneDetail(sc.getAttribute("data-scene-id"));
    }
    const res = e.target.closest?.("[data-resolve]");
    if (res) {
      resolveConflictUi(res.getAttribute("data-resolve"), res.getAttribute("data-choice"));
    }
    const lock = e.target.closest?.("[data-lock-entity]");
    if (lock) {
      lockEntityValue(
        lock.getAttribute("data-lock-entity"),
        lock.getAttribute("data-field"),
        lock.getAttribute("data-original")
      );
    }
    const copyP = e.target.closest?.("[data-copy-prompt]");
    if (copyP && current?.sceneDetail?.shots) {
      const shot = current.sceneDetail.shots.find((s) => s.shot_id === copyP.getAttribute("data-copy-prompt"));
      if (shot?.prompt_preview) {
        navigator.clipboard?.writeText(shot.prompt_preview);
        showAlert("Prompt copied.", { kind: "ok" });
      }
    }
    const copyT = e.target.closest?.("[data-copy-text]");
    if (copyT) {
      navigator.clipboard?.writeText(copyT.getAttribute("data-copy-text") || "");
      showAlert("Copied.", { kind: "ok" });
    }
  });

  $("btn-import")?.addEventListener("click", () => $("script-file").click());
  $("btn-import-active")?.addEventListener("click", () => $("script-file").click());
  $("script-file")?.addEventListener("change", (e) => {
    const f = e.target.files?.[0];
    handleFile(f);
    e.target.value = "";
  });
  $("btn-sample")?.addEventListener("click", () => {
    $("script").value = SAMPLE_SCRIPT;
    setFormatLabels("fountain");
  });
  $("btn-sample-active")?.addEventListener("click", () => {
    applyImportedText(SAMPLE_SCRIPT, "sample.fountain");
  });
  $("btn-clear")?.addEventListener("click", () => {
    $("script").value = "";
  });

  const dz = $("dropzone");
  const scriptEl = $("script");
  ["dragenter", "dragover"].forEach((ev) => {
    dz?.addEventListener(ev, (e) => {
      e.preventDefault();
      dz.classList.add("is-drag");
    });
    scriptEl?.addEventListener(ev, (e) => e.preventDefault());
  });
  ["dragleave", "drop"].forEach((ev) => {
    dz?.addEventListener(ev, (e) => {
      e.preventDefault();
      dz.classList.remove("is-drag");
      if (ev === "drop" && e.dataTransfer?.files?.[0]) handleFile(e.dataTransfer.files[0]);
    });
  });
  $("script-active")?.addEventListener("dragover", (e) => e.preventDefault());
  $("script-active")?.addEventListener("drop", (e) => {
    e.preventDefault();
    if (e.dataTransfer?.files?.[0]) handleFile(e.dataTransfer.files[0]);
  });

  $("btn-analyze")?.addEventListener("click", analyzeScript);
  $("btn-analyze-sticky")?.addEventListener("click", analyzeScript);
  $("btn-review-breakdown")?.addEventListener("click", () => setView("scenes"));
  $("btn-prepare-scene")?.addEventListener("click", prepareSelectedScene);
  $("btn-scene-prev")?.addEventListener("click", () => {
    if (current?.sceneDetail?.prev_scene_id) loadSceneDetail(current.sceneDetail.prev_scene_id);
  });
  $("btn-scene-next")?.addEventListener("click", () => {
    if (current?.sceneDetail?.next_scene_id) loadSceneDetail(current.sceneDetail.next_scene_id);
  });

  document.querySelectorAll(".tabs__btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      continuityTab = btn.getAttribute("data-ctab");
      renderContinuity();
    });
  });

  $("btn-export-json")?.addEventListener("click", exportBreakdownJson);
  $("btn-export-md")?.addEventListener("click", exportBreakdownMd);
  $("btn-export-shot-list")?.addEventListener("click", exportShotListMd);
  $("btn-export-conflict-report")?.addEventListener("click", exportConflictReport);
  $("btn-export-scene-pkg")?.addEventListener("click", exportScenePackage);
  $("btn-export-from-gen")?.addEventListener("click", () => {
    if (current?.scenePackage) exportScenePackage();
    else setView("export");
  });
  $("btn-download-pkg")?.addEventListener("click", exportScenePackage);
  $("btn-copy-prompts")?.addEventListener("click", () => {
    const prompts = (current?.scenePackage?.shot_prompts || []).map((p) => p.prompt).join("\n\n");
    navigator.clipboard?.writeText(prompts || "");
    showAlert("Prompts copied.", { kind: "ok" });
  });

  $("btn-settings")?.addEventListener("click", () => {
    updateDevPanels();
    pingHealth();
    $("settings-dialog").showModal();
  });
  $("btn-open-dev-providers")?.addEventListener("click", () => {
    $("settings-dialog").showModal();
  });
  $("btn-mock-proof")?.addEventListener("click", runMockProof);
  $("btn-inv-cancel")?.addEventListener("click", () => {
    pendingOverride = null;
    $("invalidation-dialog").close();
  });
  $("btn-inv-confirm")?.addEventListener("click", confirmOverride);

  $("btn-change-script")?.addEventListener("click", () => {
    $("script-panel")?.scrollIntoView({ behavior: "smooth", block: "start" });
    $("script-active")?.focus();
  });

  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      if (current && !$("project-workspace").hidden) {
        e.preventDefault();
        analyzeScript();
      }
    }
  });
}

function init() {
  loadProjects();
  bindEvents();
  updateProjectChrome();
  const last = localStorage.getItem(LAST_KEY);
  if (last && projects[last]) {
    openProject(last);
  } else {
    showEmptyState();
  }
  setView("projects");
  pingHealth();
}

document.addEventListener("DOMContentLoaded", init);
