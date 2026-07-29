/**
 * Continuity Forge · Proof Workbench (easy path)
 * Default: paste script → Run proof → read receipt.
 * Advanced: connection, canon, leases, approvals.
 * Long-form 4.1: scene / shot navigation (read-only).
 * Long-form 4.2: virtualized shot table + filters (presentation only).
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

const $ = (id) => document.getElementById(id);

/** @type {Record<string, any> | null} */
let lastReceipt = null;
/** @type {Record<string, any> | null} */
let lastWhoami = null;

/** Scene/shot navigation state (read-only; does not mutate canon). */
const nav = {
  /** @type {string[]} ordered unique scene_ids from receipt shots */
  sceneIds: [],
  /** @type {Map<string, {scene_id: string, label: string, count: number}>} */
  scenes: new Map(),
  /** null = all scenes */
  focusSceneId: /** @type {string | null} */ (null),
  /** index into filtered shot list for keyboard focus highlight */
  focusShotIndex: 0,
};

/** Table view: filters + virtualization (presentation only). */
const tableView = {
  statusFilter: "all",
  repairFilter: "all",
  sort: "default",
  /** Feature flag: when false, mount every row (short proofs). */
  virtualEnabled: true,
  /** Auto-enable virtualization when logical row count exceeds this. */
  virtualThreshold: 40,
  rowHeight: 44,
  overscan: 8,
  scrollTop: 0,
  _boundScroll: false,
  /** @type {Set<string>} shot_ids marked stale by invalidation preview */
  staleShotIds: new Set(),
};

/** Last full IR document for incremental compile prior reconcile (session only). */
let lastCompiledDocument = null;

/** Last breakdown package (handoff export). */
let lastBreakdown = null;
let lastBreakdownMarkdown = null;

const els = {
  script: $("script"),
  documentKey: $("document-key"),
  title: $("title"),
  format: $("format"),
  seed: $("seed"),
  apiBase: $("api-base"),
  apiKey: $("api-key"),
  holder: $("holder"),
  approvalKind: $("approval-kind"),
  approvalRationale: $("approval-rationale"),
  btnProof: $("btn-proof"),
  btnBreakdown: $("btn-breakdown"),
  btnImport: $("btn-import"),
  scriptFile: $("script-file"),
  btnBreakdownSticky: $("btn-breakdown-sticky"),
  stickyCta: $("sticky-cta"),
  stickyHint: $("sticky-hint"),
  btnHealth: $("btn-health"),
  btnCompile: $("btn-compile"),
  btnCompileIncremental: $("btn-compile-incremental"),
  btnSample: $("btn-sample"),
  btnClear: $("btn-clear"),
  btnBootstrap: $("btn-bootstrap"),
  btnWhoami: $("btn-whoami"),
  btnExport: $("btn-export"),
  btnExportBreakdown: $("btn-export-breakdown"),
  btnExportBreakdownMd: $("btn-export-breakdown-md"),
  btnCopyHash: $("btn-copy-hash"),
  btnStatus: $("btn-status"),
  btnList: $("btn-list"),
  btnLeaseAcquire: $("btn-lease-acquire"),
  btnLeaseRelease: $("btn-lease-release"),
  btnLeaseRefresh: $("btn-lease-refresh"),
  btnApprovalRequest: $("btn-approval-request"),
  btnApprovalsList: $("btn-approvals-list"),
  btnRunsList: $("btn-runs-list"),
  runState: $("run-state"),
  runMeta: $("run-meta"),
  metaElapsed: $("meta-elapsed"),
  metaBudget: $("meta-budget"),
  metaWithin: $("meta-within"),
  metaShots: $("meta-shots"),
  metaCost: $("meta-cost"),
  workflowPanel: $("workflow-panel"),
  workflowStepLabel: $("workflow-step-label"),
  workflowPercent: $("workflow-percent"),
  workflowBar: $("workflow-bar"),
  workflowFill: $("workflow-fill"),
  workflowRunId: $("workflow-run-id"),
  workflowStatus: $("workflow-status"),
  workflowLastOk: $("workflow-last-ok"),
  workflowError: $("workflow-error"),
  workflowEvents: $("workflow-events"),
  workflowHint: $("workflow-hint"),
  alert: $("alert"),
  chipHealth: $("chip-health"),
  chipBackend: $("chip-backend"),
  chipVersion: $("chip-version"),
  chipTenant: $("chip-tenant"),
  receiptEmpty: $("receipt-empty"),
  receiptBody: $("receipt-body"),
  receiptExec: $("receipt-exec"),
  receiptBudget: $("receipt-budget"),
  receiptClaim: $("receipt-claim"),
  resultStack: $("result-stack"),
  resultBanner: $("result-banner"),
  claimPostProof: $("claim-post-proof"),
  claimExecLabel: $("claim-exec-label"),
  claimBudgetLabel: $("claim-budget-label"),
  costPanel: $("cost-panel"),
  costTotal: $("cost-total"),
  costEvents: $("cost-events"),
  costRetries: $("cost-retries"),
  costProviders: $("cost-providers"),
  costAuthorityNote: $("cost-authority-note"),
  rClaimCode: $("r-claim-code"),
  rClaim: $("r-claim"),
  rDoc: $("r-doc"),
  rHash: $("r-hash"),
  rSchema: $("r-schema"),
  rSource: $("r-source"),
  rIr: $("r-ir"),
  rLedger: $("r-ledger"),
  rShotsHash: $("r-shots-hash"),
  shotRows: $("shot-rows"),
  shotEmpty: $("shot-empty"),
  shotTableWrap: $("shot-table-wrap"),
  shotToolbar: $("shot-toolbar"),
  shotToolbarMeta: $("shot-toolbar-meta"),
  shotFilterStatus: $("shot-filter-status"),
  shotFilterRepair: $("shot-filter-repair"),
  shotSort: $("shot-sort"),
  shotVirtual: $("shot-virtual"),
  sceneNav: $("scene-nav"),
  sceneList: $("scene-list"),
  sceneFocusLabel: $("scene-focus-label"),
  btnSceneAll: $("btn-scene-all"),
  btnScenePrev: $("btn-scene-prev"),
  btnSceneNext: $("btn-scene-next"),
  btnStalePreview: $("btn-stale-preview"),
  btnStaleClear: $("btn-stale-clear"),
  rawJson: $("raw-json"),
  statusGrid: $("status-grid"),
  stDoc: $("st-doc"),
  stTitle: $("st-title"),
  stCounts: $("st-counts"),
  stSource: $("st-source"),
  stState: $("st-state"),
  stRun: $("st-run"),
  projectListWrap: $("project-list-wrap"),
  projectRows: $("project-rows"),
  canonEmpty: $("canon-empty"),
  leaseGrid: $("lease-grid"),
  leaseActive: $("lease-active"),
  leaseHolder: $("lease-holder"),
  leaseScope: $("lease-scope"),
  leaseExpires: $("lease-expires"),
  approvalListWrap: $("approval-list-wrap"),
  approvalEmpty: $("approval-empty"),
  approvalTable: $("approval-table"),
  approvalRows: $("approval-rows"),
  runListWrap: $("run-list-wrap"),
  runRows: $("run-rows"),
  controlEmpty: $("control-empty"),
};

/** Map repair action codes → short operator rationale labels. */
const REPAIR_ACTION_RATIONALE = {
  regenerate: "Regenerate candidate after validator failure",
  include_missing_entities: "Include missing required entities",
  drop_soft_target: "Drop soft target to satisfy constraints",
};

function baseUrl() {
  return (els.apiBase.value || "").trim().replace(/\/$/, "");
}

function headers() {
  const h = { "Content-Type": "application/json", Accept: "application/json" };
  const key = (els.apiKey.value || "").trim();
  if (key) {
    h.Authorization = key.startsWith("Bearer ") ? key : `Bearer ${key}`;
  }
  return h;
}

function showAlert(message, kind = "error") {
  els.alert.hidden = !message;
  els.alert.textContent = message || "";
  els.alert.className = `alert alert--${kind}`;
}

function setRunState(state, label) {
  if (!els.runState) return;
  els.runState.dataset.state = state;
  els.runState.textContent = label;
  els.runState.className =
    "chip " +
    (state === "done"
      ? "chip--ok"
      : state === "error"
        ? "chip--danger"
        : state === "running"
          ? "chip--accent"
          : "chip--accent");
  if (els.stickyHint) {
    els.stickyHint.textContent =
      state === "running"
        ? "Working…"
        : state === "done"
          ? "Done"
          : state === "error"
            ? "Failed"
            : "Script ready — Build breakdown";
  }
}

function setBreakdownButtons({ disabled, state, label }) {
  if (els.btnBreakdown) {
    els.btnBreakdown.disabled = !!disabled;
    if (label) els.btnBreakdown.textContent = label;
  }
  if (els.btnBreakdownSticky) {
    els.btnBreakdownSticky.disabled = !!disabled;
    if (label) els.btnBreakdownSticky.textContent = label;
  }
  if (state) setRunState(state, state === "running" ? "building" : state);
}

function setStep(n) {
  for (let i = 1; i <= 3; i++) {
    const el = $(`step-${i}`);
    if (!el) continue;
    el.classList.remove("is-current", "is-done");
    if (i < n) el.classList.add("is-done");
    if (i === n) el.classList.add("is-current");
  }
}

function humanStatus(status) {
  if (!status) return "—";
  if (status === "accepted_proposed") return "accepted (proposed)";
  return status.replaceAll("_", " ");
}

/**
 * Build a validator/repair rationale summary when repair_actions are present.
 * Prefers shot.repair_rationale / shot.validator_rationale if the receipt
 * includes them; otherwise derives labels from action codes.
 */
function repairRationaleSummary(shot) {
  const actions = Array.isArray(shot?.repair_actions) ? shot.repair_actions : [];
  if (!actions.length) return null;

  const explicit =
    (typeof shot.repair_rationale === "string" && shot.repair_rationale.trim()) ||
    (typeof shot.validator_rationale === "string" &&
      shot.validator_rationale.trim()) ||
    "";
  if (explicit) {
    return { actions, rationale: explicit };
  }

  const unique = [...new Set(actions.map((a) => String(a)))];
  const labels = unique.map(
    (code) => REPAIR_ACTION_RATIONALE[code] || humanStatus(code),
  );
  return {
    actions: unique,
    rationale: labels.join(" · "),
  };
}

function setProofButtons(opts) {
  const { disabled, state, label } = opts;
  for (const btn of [els.btnProof, els.btnProofSticky]) {
    if (!btn) continue;
    btn.disabled = !!disabled;
    if (state !== undefined) btn.dataset.state = state || "";
    if (label !== undefined) btn.textContent = label;
  }
}

function shortHash(value) {
  if (!value) return "—";
  const s = String(value);
  return s.length > 16 ? `${s.slice(0, 12)}…${s.slice(-4)}` : s;
}

function setText(el, value) {
  el.textContent = value == null || value === "" ? "—" : String(value);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function activeDocumentKey() {
  const raw = (els.documentKey.value || "").trim();
  if (raw) return raw;
  if (lastReceipt && lastReceipt.document_key) {
    const full = String(lastReceipt.document_key);
    const parts = full.split("::");
    return parts.length > 1 ? parts.slice(1).join("::") : full;
  }
  return "";
}

function actorId() {
  const fromField = (els.holder?.value || "").trim();
  if (fromField) return fromField;
  if (lastWhoami?.actor_id) return String(lastWhoami.actor_id);
  return "proof-ui";
}

function requireDocumentKey() {
  const key = activeDocumentKey();
  if (!key) {
    throw new Error("Set a Project ID under Script options first.");
  }
  return key;
}

function idempotencyKey(prefix) {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

async function api(path, options = {}) {
  const url = `${baseUrl()}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: { ...headers(), ...(options.headers || {}) },
  });
  let body = null;
  const text = await res.text();
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = { detail: text };
    }
  }
  if (!res.ok) {
    const detail =
      (body && (body.detail || body.message)) || `${res.status} ${res.statusText}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return body;
}

async function pingHealth() {
  try {
    const data = await api("/health");
    els.chipHealth.textContent = `api · ${data.status || "ok"}`;
    els.chipHealth.className = "chip chip--ok";
    els.chipBackend.textContent = `backend · ${data.backend || "—"}`;
    els.chipVersion.textContent = `v · ${data.version || "—"}`;
    return data;
  } catch (err) {
    els.chipHealth.textContent = "api · offline";
    els.chipHealth.className = "chip chip--danger";
    els.chipBackend.textContent = "backend · —";
    els.chipVersion.textContent = "v · —";
    throw err;
  }
}

async function pingWhoami() {
  try {
    const data = await api("/v1/whoami");
    lastWhoami = data;
    if (els.chipTenant) {
      els.chipTenant.hidden = false;
      els.chipTenant.textContent = `tenant · ${data.tenant_id || "—"}`;
      els.chipTenant.className = "chip chip--accent";
    }
    if (data.actor_id && els.holder && els.holder.value === "proof-ui") {
      /* keep default proof-ui unless user customized */
    }
    return data;
  } catch {
    lastWhoami = null;
    if (els.chipTenant) {
      els.chipTenant.hidden = true;
    }
    return null;
  }
}

function showControl() {
  if (els.controlEmpty) els.controlEmpty.hidden = true;
}

function renderLease(payload) {
  showControl();
  els.leaseGrid.hidden = false;
  if (!payload.active || !payload.lease) {
    setText(els.leaseActive, "inactive");
    setText(els.leaseHolder, "—");
    setText(els.leaseScope, "—");
    setText(els.leaseExpires, "—");
    return;
  }
  setText(els.leaseActive, "active");
  setText(els.leaseHolder, payload.lease.holder);
  setText(els.leaseScope, payload.lease.scope);
  setText(els.leaseExpires, payload.lease.expires_at);
}

function renderApprovals(payload) {
  showControl();
  els.approvalListWrap.hidden = false;
  els.approvalRows.replaceChildren();
  const rows = payload.approvals || [];
  if (!rows.length) {
    if (els.approvalEmpty) els.approvalEmpty.hidden = false;
    if (els.approvalTable) els.approvalTable.hidden = true;
    return;
  }
  if (els.approvalEmpty) els.approvalEmpty.hidden = true;
  if (els.approvalTable) els.approvalTable.hidden = false;
  for (const a of rows) {
    const tr = document.createElement("tr");
    const status = a.status || "";
    const statusClass =
      status === "granted"
        ? "status-ok"
        : status === "denied"
          ? "status-fail"
          : "";
    tr.innerHTML = `
      <td>${escapeHtml(a.kind || "—")}</td>
      <td class="${statusClass}">${escapeHtml(status)}</td>
      <td>${escapeHtml(a.actor_id || "—")}</td>
      <td title="${escapeHtml(a.approval_id || "")}">${escapeHtml(
        shortHash(a.approval_id),
      )}</td>
      <td class="decide-cell"></td>
    `;
    const cell = tr.querySelector(".decide-cell");
    if (status === "requested" && cell) {
      const grant = document.createElement("button");
      grant.type = "button";
      grant.className = "btn btn--ghost";
      grant.textContent = "Grant";
      grant.addEventListener("click", () => {
        decideApproval(a.approval_id, "granted").catch((err) =>
          showAlert(err instanceof Error ? err.message : String(err)),
        );
      });
      const deny = document.createElement("button");
      deny.type = "button";
      deny.className = "btn btn--ghost";
      deny.textContent = "Deny";
      deny.addEventListener("click", () => {
        decideApproval(a.approval_id, "denied").catch((err) =>
          showAlert(err instanceof Error ? err.message : String(err)),
        );
      });
      cell.append(grant, deny);
    } else if (cell) {
      cell.textContent = "—";
    }
    els.approvalRows.appendChild(tr);
  }
}

/** Poll cursor for workflow events (resume without re-mutation). */
const workflowPoll = {
  runId: null,
  afterSequence: 0,
  lastEventId: null,
  events: [],
  timer: null,
};

function stopWorkflowPoll() {
  if (workflowPoll.timer) {
    window.clearInterval(workflowPoll.timer);
    workflowPoll.timer = null;
  }
}

function renderWorkflowProgress(page) {
  if (!els.workflowPanel) return;
  els.workflowPanel.hidden = false;
  const progress = page.progress || {};
  const percent = Number(progress.percent || 0);
  const label =
    progress.current_label ||
    progress.current_step ||
    page.status ||
    "—";
  setText(els.workflowStepLabel, label);
  setText(els.workflowPercent, `${percent}%`);
  if (els.workflowFill) {
    els.workflowFill.style.width = `${Math.max(0, Math.min(100, percent))}%`;
    els.workflowFill.classList.toggle(
      "workflow-progress__fill--fail",
      page.status === "failed",
    );
  }
  if (els.workflowBar) {
    els.workflowBar.setAttribute("aria-valuenow", String(percent));
  }
  setText(els.workflowRunId, shortHash(page.run_id || workflowPoll.runId));
  setText(els.workflowStatus, page.status || progress.run_status || "—");
  setText(
    els.workflowLastOk,
    progress.last_successful_checkpoint || "—",
  );
  const err =
    progress.error_message ||
    (progress.error_code ? progress.error_code : null);
  setText(els.workflowError, err || "—");
  if (els.workflowHint) {
    els.workflowHint.textContent =
      "Workflow complete ≠ production ready · poll observability · not film canon";
  }
  if (els.workflowEvents) {
    els.workflowEvents.replaceChildren();
    const list = workflowPoll.events;
    for (const ev of list) {
      const li = document.createElement("li");
      const step = ev.label || ev.step || ev.kind || "event";
      li.textContent = `${ev.sequence}. ${ev.kind} · ${step}` +
        (ev.status ? ` · ${ev.status}` : "");
      els.workflowEvents.appendChild(li);
    }
  }
}

async function pollWorkflowEvents(runId, { reset = false } = {}) {
  if (!runId) return;
  if (reset) {
    workflowPoll.runId = runId;
    workflowPoll.afterSequence = 0;
    workflowPoll.lastEventId = null;
    workflowPoll.events = [];
  }
  const params = new URLSearchParams();
  if (workflowPoll.lastEventId) {
    params.set("last_event_id", workflowPoll.lastEventId);
  } else if (workflowPoll.afterSequence > 0) {
    params.set("after", String(workflowPoll.afterSequence));
  }
  const qs = params.toString() ? `?${params}` : "";
  const page = await api(
    `/v1/pipeline/runs/${encodeURIComponent(runId)}/events${qs}`,
  );
  const batch = page.events || [];
  for (const ev of batch) {
    workflowPoll.events.push(ev);
  }
  if (page.last_event_id) {
    workflowPoll.lastEventId = page.last_event_id;
  }
  if (page.next_after_sequence != null) {
    workflowPoll.afterSequence = page.next_after_sequence;
  }
  renderWorkflowProgress(page);
  const terminal =
    page.status === "completed" ||
    page.status === "failed" ||
    page.status === "cancelled";
  if (terminal) {
    stopWorkflowPoll();
  }
  return page;
}

function startWorkflowPoll(runId) {
  stopWorkflowPoll();
  pollWorkflowEvents(runId, { reset: true }).catch((err) =>
    showAlert(err instanceof Error ? err.message : String(err)),
  );
  // Short polls for in-process runs that may already be complete on first hit.
  workflowPoll.timer = window.setInterval(() => {
    if (!workflowPoll.runId) return;
    pollWorkflowEvents(workflowPoll.runId).catch(() => stopWorkflowPoll());
  }, 1500);
}

function renderRuns(payload) {
  showControl();
  els.runListWrap.hidden = false;
  els.runRows.replaceChildren();
  const rows = payload.runs || [];
  if (!rows.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td colspan="4">No pipeline runs for ${escapeHtml(
      payload.document_key || "—",
    )}</td>`;
    els.runRows.appendChild(tr);
    return;
  }
  for (const r of rows) {
    const tr = document.createElement("tr");
    tr.className = "run-row";
    tr.tabIndex = 0;
    tr.title = "Click to poll workflow events";
    const status = r.status || "—";
    const created = r.created_at || r.started_at || "—";
    const idem = r.command?.idempotency_key || "—";
    tr.innerHTML = `
      <td title="${escapeHtml(r.run_id || "")}">${escapeHtml(shortHash(r.run_id))}</td>
      <td>${escapeHtml(status)}</td>
      <td>${escapeHtml(idem)}</td>
      <td>${escapeHtml(created)}</td>
    `;
    const open = () => {
      els.runRows.querySelectorAll(".run-row-active").forEach((el) => {
        el.classList.remove("run-row-active");
      });
      tr.classList.add("run-row-active");
      if (r.run_id) {
        startWorkflowPoll(r.run_id);
        showAlert(
          `Polling workflow events · ${shortHash(r.run_id)} · not production ready`,
          "ok",
        );
      }
    };
    tr.addEventListener("click", open);
    tr.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        open();
      }
    });
    els.runRows.appendChild(tr);
  }
}

async function refreshLease() {
  const key = requireDocumentKey();
  const payload = await api(`/v1/projects/${encodeURIComponent(key)}/lease`);
  renderLease(payload);
  return payload;
}

async function acquireLease() {
  const key = requireDocumentKey();
  const holder = actorId();
  const lease = await api("/v1/projects/lease", {
    method: "POST",
    body: JSON.stringify({
      document_key: key,
      holder,
      scope: "project",
      ttl_seconds: 600,
    }),
  });
  renderLease({ active: true, lease, document_key: lease.document_key });
  showAlert(`Lease acquired · holder ${lease.holder}`, "ok");
}

async function releaseLease() {
  const key = requireDocumentKey();
  const holder = actorId();
  await api(
    `/v1/projects/${encodeURIComponent(key)}/lease?holder=${encodeURIComponent(holder)}`,
    { method: "DELETE" },
  );
  await refreshLease();
  showAlert(`Lease released · holder ${holder}`, "ok");
}

async function requestApproval() {
  const key = requireDocumentKey();
  const actor = actorId();
  const record = await api("/v1/approvals/request", {
    method: "POST",
    body: JSON.stringify({
      document_key: key,
      kind: (els.approvalKind.value || "commit_candidate").trim(),
      actor_id: actor,
      authorization_scope: "approvals",
      idempotency_key: idempotencyKey("appr"),
      rationale: (els.approvalRationale.value || "operator decision").trim(),
    }),
  });
  showAlert(`Approval requested · ${shortHash(record.approval_id)}`, "ok");
  await listApprovals();
}

async function decideApproval(approvalId, status) {
  const actor = actorId();
  const record = await api("/v1/approvals/decide", {
    method: "POST",
    body: JSON.stringify({
      approval_id: approvalId,
      status,
      actor_id: actor,
      authorization_scope: "approvals",
      idempotency_key: idempotencyKey(`dec-${status}`),
      rationale: (els.approvalRationale.value || `decision:${status}`).trim(),
    }),
  });
  showAlert(`Approval ${status} · ${shortHash(record.approval_id)}`, "ok");
  await listApprovals();
}

async function listApprovals() {
  const key = requireDocumentKey();
  const payload = await api(`/v1/projects/${encodeURIComponent(key)}/approvals`);
  renderApprovals(payload);
  showAlert(`Approvals · ${(payload.approvals || []).length}`, "ok");
}

async function listRuns() {
  const key = requireDocumentKey();
  const payload = await api(`/v1/projects/${encodeURIComponent(key)}/runs`);
  renderRuns(payload);
  showAlert(`Runs · ${(payload.runs || []).length}`, "ok");
}

function buildSceneIndex(shots) {
  nav.scenes = new Map();
  nav.sceneIds = [];
  for (const shot of shots) {
    const sid = String(shot.scene_id || "unknown");
    if (!nav.scenes.has(sid)) {
      nav.scenes.set(sid, {
        scene_id: sid,
        label: sceneLabelFromShot(shot, sid),
        count: 0,
      });
      nav.sceneIds.push(sid);
    }
    const entry = nav.scenes.get(sid);
    entry.count += 1;
    // Prefer a scene-like label if shot label encodes scene-NNN-master
    if (shot.label && String(shot.label).includes("scene-")) {
      entry.label = sceneLabelFromShot(shot, sid);
    }
  }
}

function sceneLabelFromShot(shot, sceneId) {
  const label = String(shot.label || "");
  const m = label.match(/^(scene-\d+)/i);
  if (m) return m[1];
  return shortHash(sceneId);
}

function sceneFilteredShots() {
  const shots = lastReceipt?.shots || [];
  if (!nav.focusSceneId) return shots.slice();
  return shots.filter((s) => String(s.scene_id || "") === nav.focusSceneId);
}

/** Logical shot list: scene focus + status/repair filters + sort. */
function logicalShots() {
  let shots = sceneFilteredShots();

  if (tableView.statusFilter === "accept") {
    shots = shots.filter((s) => String(s.status || "").includes("accept"));
  } else if (tableView.statusFilter === "fail") {
    shots = shots.filter((s) => !String(s.status || "").includes("accept"));
  }

  if (tableView.repairFilter === "yes") {
    shots = shots.filter(
      (s) => Array.isArray(s.repair_actions) && s.repair_actions.length > 0,
    );
  } else if (tableView.repairFilter === "no") {
    shots = shots.filter(
      (s) => !Array.isArray(s.repair_actions) || s.repair_actions.length === 0,
    );
  }

  if (tableView.sort === "label") {
    shots.sort((a, b) =>
      String(a.label || "").localeCompare(String(b.label || "")),
    );
  } else if (tableView.sort === "status") {
    shots.sort((a, b) =>
      String(a.status || "").localeCompare(String(b.status || "")),
    );
  } else if (tableView.sort === "attempts") {
    shots.sort((a, b) => Number(b.attempts || 0) - Number(a.attempts || 0));
  }

  return shots;
}

/** @deprecated use logicalShots — kept name for call sites */
function filteredShots() {
  return logicalShots();
}

function useVirtualization(rowCount) {
  if (!tableView.virtualEnabled) return false;
  return rowCount >= tableView.virtualThreshold;
}

function buildShotRow(shot, index) {
  const tr = document.createElement("tr");
  if (index === nav.focusShotIndex) tr.classList.add("shot-row-focus");
  const shotKey = String(shot.shot_id || "");
  const isStale = tableView.staleShotIds.has(shotKey);
  if (isStale) tr.classList.add("shot-row-stale");
  tr.dataset.shotId = shotKey;
  tr.dataset.sceneId = String(shot.scene_id || "");
  tr.dataset.rowIndex = String(index);
  const status = shot.status || "";
  const statusClass =
    status.includes("accept") || status === "accepted_proposed"
      ? "status-ok"
      : status.includes("fail") || status.includes("reject")
        ? "status-fail"
        : "";
  const summary = repairRationaleSummary(shot);
  let repairCell = "—";
  if (summary) {
    const actionCodes = summary.actions
      .map((a) => escapeHtml(String(a)))
      .join(", ");
    repairCell = `
      <div class="repair-summary">
        <span class="repair-summary__actions">${actionCodes}</span>
        <span class="repair-summary__rationale">${escapeHtml(summary.rationale)}</span>
      </div>
    `;
  }
  const staleBadge = isStale
    ? `<span class="stale-badge" title="Lineage retained; not elevated to canon">stale</span>`
    : "—";
  tr.innerHTML = `
    <td>${escapeHtml(shot.label || shortHash(shot.shot_id))}</td>
    <td class="${statusClass}">${escapeHtml(humanStatus(status))}</td>
    <td>${escapeHtml(String(shot.attempts ?? "—"))}</td>
    <td>${repairCell}</td>
    <td title="${escapeHtml(shot.accepted_candidate_hash || "")}">${escapeHtml(
      shortHash(shot.accepted_candidate_hash),
    )}</td>
    <td>${staleBadge}</td>
  `;
  tr.addEventListener("click", () => {
    nav.focusShotIndex = index;
    renderShotTable();
    syncNavUrl();
    announceShotFocus();
  });
  return tr;
}

async function previewStaleForFocus() {
  showAlert("");
  const text = els.script.value.trim();
  if (!text) {
    showAlert("Script required for invalidation preview.");
    return;
  }
  const change = {
    source_changed: false,
    scene_ids: nav.focusSceneId ? [nav.focusSceneId] : [],
    atom_ids: [],
    entity_ids: [],
    fact_ids: [],
    shot_ids: [],
  };
  if (!nav.focusSceneId) {
    // All scenes: treat as full source change for demo of force subgraph
    change.source_changed = true;
  }
  try {
    const payload = await api("/v1/invalidation/preview", {
      method: "POST",
      body: JSON.stringify({
        title: els.title.value.trim() || "Untitled",
        text,
        document_key: els.documentKey.value.trim() || null,
        format: els.format.value,
        change,
        force_full: false,
      }),
    });
    const ids = payload.stale_shot_ids || [];
    tableView.staleShotIds = new Set(ids.map(String));
    renderShotTable();
    showAlert(
      `Invalidation preview · ${ids.length} shot(s) stale · not a canon write · PROPOSED not elevated`,
      "ok",
    );
  } catch (err) {
    showAlert(err instanceof Error ? err.message : String(err));
  }
}

function clearStaleMarks() {
  tableView.staleShotIds = new Set();
  renderShotTable();
  showAlert("Cleared stale markers (hashes retained).", "ok");
}

function announceShotFocus() {
  const shots = logicalShots();
  const shot = shots[nav.focusShotIndex];
  if (!shot || !els.shotToolbarMeta) return;
  // live region update is on toolbar meta
  const mode = useVirtualization(shots.length) ? "virtual" : "full";
  els.shotToolbarMeta.textContent = `${shots.length} row(s) · ${mode} · focus ${nav.focusShotIndex + 1}/${shots.length} · ${shot.label || shortHash(shot.shot_id)} · not production film`;
}

function updateShotToolbar(shots) {
  if (!els.shotToolbar) return;
  if (!lastReceipt) {
    els.shotToolbar.hidden = true;
    return;
  }
  els.shotToolbar.hidden = false;
  if (els.shotVirtual) {
    els.shotVirtual.checked = tableView.virtualEnabled;
  }
  announceShotFocus();
  if (!shots.length && els.shotToolbarMeta) {
    els.shotToolbarMeta.textContent = "0 rows match filters · presentation only";
  }
}

function renderShotTableFull(shots) {
  els.shotRows.replaceChildren();
  shots.forEach((shot, index) => {
    els.shotRows.appendChild(buildShotRow(shot, index));
  });
}

function renderShotTableVirtual(shots) {
  const wrap = els.shotTableWrap;
  if (!wrap || !els.shotRows) {
    renderShotTableFull(shots);
    return;
  }

  const viewportH = wrap.clientHeight || 400;
  const rowH = tableView.rowHeight;
  const total = shots.length;
  const totalH = total * rowH;
  const scrollTop = wrap.scrollTop;
  tableView.scrollTop = scrollTop;

  let start = Math.floor(scrollTop / rowH) - tableView.overscan;
  if (start < 0) start = 0;
  let end = Math.ceil((scrollTop + viewportH) / rowH) + tableView.overscan;
  if (end > total) end = total;

  // Keep focused row mounted for a11y
  if (nav.focusShotIndex >= 0 && nav.focusShotIndex < total) {
    if (nav.focusShotIndex < start) start = nav.focusShotIndex;
    if (nav.focusShotIndex >= end) end = nav.focusShotIndex + 1;
  }

  const topPad = start * rowH;
  const bottomPad = Math.max(0, totalH - end * rowH);

  els.shotRows.replaceChildren();

  if (topPad > 0) {
    const spacer = document.createElement("tr");
    spacer.className = "shot-spacer shot-spacer--top";
    spacer.setAttribute("aria-hidden", "true");
    const td = document.createElement("td");
    td.colSpan = 6;
    td.style.height = `${topPad}px`;
    spacer.appendChild(td);
    els.shotRows.appendChild(spacer);
  }

  for (let i = start; i < end; i++) {
    els.shotRows.appendChild(buildShotRow(shots[i], i));
  }

  if (bottomPad > 0) {
    const spacer = document.createElement("tr");
    spacer.className = "shot-spacer shot-spacer--bottom";
    spacer.setAttribute("aria-hidden", "true");
    const td = document.createElement("td");
    td.colSpan = 6;
    td.style.height = `${bottomPad}px`;
    spacer.appendChild(td);
    els.shotRows.appendChild(spacer);
  }

  if (!tableView._boundScroll) {
    wrap.addEventListener(
      "scroll",
      () => {
        if (!lastReceipt) return;
        if (!useVirtualization(logicalShots().length)) return;
        renderShotTable();
      },
      { passive: true },
    );
    tableView._boundScroll = true;
  }
}

function syncNavUrl() {
  try {
    const url = new URL(window.location.href);
    const doc = activeDocumentKey();
    if (doc) url.searchParams.set("document_key", doc);
    else url.searchParams.delete("document_key");
    if (nav.focusSceneId) url.searchParams.set("scene_id", nav.focusSceneId);
    else url.searchParams.delete("scene_id");
    const shots = filteredShots();
    const focused = shots[nav.focusShotIndex];
    if (focused?.shot_id) url.searchParams.set("shot_id", String(focused.shot_id));
    else url.searchParams.delete("shot_id");
    history.replaceState(null, "", url.pathname + url.search + url.hash);
  } catch {
    /* ignore */
  }
}

function applyNavFromUrl() {
  try {
    const url = new URL(window.location.href);
    const doc = url.searchParams.get("document_key");
    if (doc && els.documentKey) els.documentKey.value = doc;
    const sceneId = url.searchParams.get("scene_id");
    const shotId = url.searchParams.get("shot_id");
    if (sceneId && nav.sceneIds.includes(sceneId)) {
      nav.focusSceneId = sceneId;
    }
    if (shotId && lastReceipt) {
      const list = filteredShots();
      const idx = list.findIndex((s) => String(s.shot_id) === shotId);
      if (idx >= 0) nav.focusShotIndex = idx;
    }
  } catch {
    /* ignore */
  }
}

function renderSceneNav() {
  if (!els.sceneNav || !els.sceneList) return;
  if (!lastReceipt || !nav.sceneIds.length) {
    els.sceneNav.hidden = true;
    return;
  }
  // Always available; short fixtures still work without requiring expand chrome
  els.sceneNav.hidden = false;
  els.sceneList.replaceChildren();

  for (const sid of nav.sceneIds) {
    const meta = nav.scenes.get(sid);
    const li = document.createElement("li");
    li.setAttribute("role", "none");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "scene-nav__item";
    btn.setAttribute("role", "option");
    btn.setAttribute(
      "aria-selected",
      nav.focusSceneId === sid ? "true" : "false",
    );
    btn.dataset.sceneId = sid;
    btn.innerHTML = `${escapeHtml(meta?.label || shortHash(sid))}<span class="scene-nav__count">(${meta?.count ?? 0})</span>`;
    btn.addEventListener("click", () => {
      setSceneFocus(sid);
    });
    li.appendChild(btn);
    els.sceneList.appendChild(li);
  }

  if (els.sceneFocusLabel) {
    if (!nav.focusSceneId) {
      els.sceneFocusLabel.textContent = `Showing all scenes · ${nav.sceneIds.length} scene(s) · ${lastReceipt.shots?.length || 0} shot(s)`;
    } else {
      const meta = nav.scenes.get(nav.focusSceneId);
      els.sceneFocusLabel.textContent = `Focused · ${meta?.label || shortHash(nav.focusSceneId)} · ${meta?.count ?? 0} shot(s) · read-only`;
    }
  }
}

function renderShotTable() {
  if (!els.shotRows) return;
  const shots = logicalShots();
  updateShotToolbar(shots);

  if (!shots.length) {
    els.shotRows.replaceChildren();
    if (els.shotEmpty) els.shotEmpty.hidden = false;
    return;
  }
  if (els.shotEmpty) els.shotEmpty.hidden = true;

  if (nav.focusShotIndex >= shots.length) {
    nav.focusShotIndex = Math.max(0, shots.length - 1);
  }
  if (nav.focusShotIndex < 0) nav.focusShotIndex = 0;

  if (useVirtualization(shots.length)) {
    renderShotTableVirtual(shots);
  } else {
    renderShotTableFull(shots);
  }
  announceShotFocus();
}

function setSceneFocus(sceneId) {
  nav.focusSceneId = sceneId || null;
  nav.focusShotIndex = 0;
  renderSceneNav();
  renderShotTable();
  syncNavUrl();
}

function stepScene(delta) {
  if (!nav.sceneIds.length) return;
  if (!nav.focusSceneId) {
    nav.focusSceneId = delta > 0 ? nav.sceneIds[0] : nav.sceneIds[nav.sceneIds.length - 1];
  } else {
    const i = nav.sceneIds.indexOf(nav.focusSceneId);
    const next = i + delta;
    if (next < 0 || next >= nav.sceneIds.length) {
      nav.focusSceneId = null; // wrap to all
    } else {
      nav.focusSceneId = nav.sceneIds[next];
    }
  }
  nav.focusShotIndex = 0;
  renderSceneNav();
  renderShotTable();
  syncNavUrl();
}

function stepShot(delta) {
  const shots = logicalShots();
  if (!shots.length) return;
  nav.focusShotIndex = Math.max(
    0,
    Math.min(shots.length - 1, nav.focusShotIndex + delta),
  );
  // Keep focused row in virtual viewport
  if (els.shotTableWrap && useVirtualization(shots.length)) {
    const targetTop = nav.focusShotIndex * tableView.rowHeight;
    const viewTop = els.shotTableWrap.scrollTop;
    const viewBottom = viewTop + els.shotTableWrap.clientHeight;
    if (targetTop < viewTop) {
      els.shotTableWrap.scrollTop = targetTop;
    } else if (targetTop + tableView.rowHeight > viewBottom) {
      els.shotTableWrap.scrollTop =
        targetTop + tableView.rowHeight - els.shotTableWrap.clientHeight;
    }
  }
  renderShotTable();
  syncNavUrl();
  const row = els.shotRows?.querySelector(".shot-row-focus");
  row?.scrollIntoView({ block: "nearest" });
  announceShotFocus();
}

function formatUsd(value) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  return `$${Number(value).toFixed(4)}`;
}

function renderCostPanel(receipt) {
  const summary = receipt.cost_summary;
  const ledger = receipt.cost_ledger;
  if (!summary && !ledger) {
    if (els.costPanel) els.costPanel.hidden = true;
    if (els.metaCost) setText(els.metaCost, "—");
    return;
  }
  if (els.costPanel) els.costPanel.hidden = false;
  const total = summary?.total_estimated_cost ?? 0;
  const events = summary?.event_count ?? (ledger?.events || []).length;
  const retries = summary?.retry_event_count ?? 0;
  const byProvider = summary?.by_provider || {};
  const providerLabel =
    Object.keys(byProvider).length > 0
      ? Object.entries(byProvider)
          .map(([k, v]) => `${k}×${v}`)
          .join(" · ")
      : "—";
  setText(els.costTotal, formatUsd(total));
  setText(els.costEvents, String(events));
  setText(
    els.costRetries,
    `${retries}` +
      (summary?.retry_estimated_cost != null
        ? ` (${formatUsd(summary.retry_estimated_cost)})`
        : ""),
  );
  setText(els.costProviders, providerLabel);
  if (els.metaCost) setText(els.metaCost, formatUsd(total));
  if (els.costAuthorityNote) {
    els.costAuthorityNote.textContent =
      summary?.authority_note ||
      "Cost ledger is run provenance only · not project canon · not production film";
  }
}

function renderReceipt(receipt) {
  lastReceipt = receipt;
  els.receiptEmpty.hidden = true;
  els.receiptBody.hidden = false;
  els.runMeta.hidden = false;
  setStep(3);

  const claim = receipt.claim || "controlled_proof_not_production_ready";
  const shots = receipt.shots || [];
  const accepted = shots.filter(
    (s) => String(s.status || "").includes("accept"),
  ).length;
  const onTime =
    receipt.within_budget === true
      ? "within budget"
      : receipt.within_budget === false
        ? "over budget"
        : "budget n/a";

  // Three-way honesty: execution · budget · production readiness.
  if (els.receiptExec) {
    els.receiptExec.textContent = "execution ok";
    els.receiptExec.className = "chip chip--ok";
  }
  if (els.receiptBudget) {
    els.receiptBudget.hidden = false;
    if (receipt.within_budget === false) {
      els.receiptBudget.textContent = "over budget";
      els.receiptBudget.className = "chip chip--danger";
    } else if (receipt.within_budget === true) {
      els.receiptBudget.textContent = "within budget";
      els.receiptBudget.className = "chip chip--ok";
    } else {
      els.receiptBudget.textContent = "budget n/a";
      els.receiptBudget.className = "chip chip--warn";
    }
  }
  if (els.receiptClaim) {
    els.receiptClaim.hidden = false;
    els.receiptClaim.textContent = "not production ready";
    els.receiptClaim.className = "chip chip--warn";
  }

  if (els.resultStack) els.resultStack.hidden = false;

  if (els.resultBanner) {
    els.resultBanner.hidden = false;
    els.resultBanner.textContent = `Execution succeeded · ${accepted}/${shots.length} shots accepted · ${onTime}`;
    els.resultBanner.className = "result-banner result-banner--exec";
  }

  if (els.claimPostProof) {
    els.claimPostProof.hidden = false;
  }
  if (els.claimExecLabel) {
    setText(
      els.claimExecLabel,
      `${accepted}/${shots.length} accepted · ${onTime}`,
    );
  }
  if (els.claimBudgetLabel) {
    const summary = receipt.cost_summary || {};
    const total =
      summary.total_estimated_cost != null
        ? `$${Number(summary.total_estimated_cost).toFixed(4)}`
        : "—";
    const budgetText =
      receipt.within_budget === false
        ? `over budget · est. ${total}`
        : receipt.within_budget === true
          ? `within budget · est. ${total}`
          : `budget n/a · est. ${total}`;
    setText(els.claimBudgetLabel, budgetText);
    els.claimBudgetLabel.className =
      "claim-banner__v" +
      (receipt.within_budget === false ? " claim-banner__v--warn" : "");
  }
  if (els.rClaimCode) {
    els.rClaimCode.textContent = claim;
  }

  setText(els.rClaim, claim);
  setText(els.rDoc, receipt.document_key);
  setText(els.rHash, receipt.receipt_hash);
  setText(els.rSchema, receipt.schema_version);
  setText(els.rSource, receipt.source_hash);
  setText(els.rIr, receipt.production_ir_hash);
  setText(els.rLedger, receipt.ledger_hash);
  setText(els.rShotsHash, receipt.shot_contracts_hash);

  const elapsed =
    typeof receipt.elapsed_seconds === "number"
      ? `${receipt.elapsed_seconds.toFixed(3)} s`
      : "—";
  setText(els.metaElapsed, elapsed);
  setText(
    els.metaBudget,
    receipt.budget_seconds != null ? `${receipt.budget_seconds} s` : "—",
  );
  setText(
    els.metaWithin,
    receipt.within_budget === true
      ? "yes"
      : receipt.within_budget === false
        ? "no"
        : "—",
  );
  setText(els.metaShots, String(shots.length));

  renderCostPanel(receipt);

  buildSceneIndex(shots);
  // Preserve URL focus if present; otherwise show all scenes
  nav.focusSceneId = null;
  nav.focusShotIndex = 0;
  applyNavFromUrl();
  renderSceneNav();
  renderShotTable();
  syncNavUrl();

  els.rawJson.textContent = JSON.stringify(receipt, null, 2);
}

function renderStatus(status) {
  els.canonEmpty.hidden = true;
  els.statusGrid.hidden = false;
  setText(els.stDoc, status.document_key);
  setText(els.stTitle, status.title);
  setText(
    els.stCounts,
    `${status.scene_count ?? "—"} / ${status.shot_count ?? "—"}`,
  );
  setText(els.stSource, status.source_hash);
  setText(els.stState, status.state_hash);
  setText(els.stRun, status.last_pipeline_run_id);
}

function renderProjectList(payload) {
  const projects = payload.projects || [];
  els.canonEmpty.hidden = true;
  els.projectListWrap.hidden = false;
  els.projectRows.replaceChildren();
  if (!projects.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td colspan="5">No projects for tenant ${escapeHtml(
      payload.tenant_id || "—",
    )}</td>`;
    els.projectRows.appendChild(tr);
    return;
  }
  for (const p of projects) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><button type="button" class="linkish" data-key="${escapeHtml(
        p.document_key,
      )}">${escapeHtml(p.document_key)}</button></td>
      <td>${escapeHtml(p.title || "—")}</td>
      <td>${escapeHtml(String(p.scene_count ?? "—"))}</td>
      <td>${escapeHtml(String(p.shot_count ?? "—"))}</td>
      <td title="${escapeHtml(p.state_hash || "")}">${escapeHtml(
        shortHash(p.state_hash),
      )}</td>
    `;
    const btn = tr.querySelector("button");
    btn?.addEventListener("click", () => {
      const full = String(p.document_key || "");
      const parts = full.split("::");
      els.documentKey.value = parts.length > 1 ? parts.slice(1).join("::") : full;
      if (p.title) els.title.value = p.title;
      loadProjectStatus().catch((err) =>
        showAlert(err instanceof Error ? err.message : String(err)),
      );
    });
    els.projectRows.appendChild(tr);
  }
}

async function runProof() {
  showAlert("");
  const text = els.script.value.trim();
  if (!text) {
    showAlert("Add a screenplay first (or click Reset sample).");
    els.script?.focus();
    setStep(1);
    return;
  }

  setStep(2);
  setProofButtons({ disabled: true, state: "loading", label: "Running…" });
  setRunState("running", "running");

  try {
    const receipt = await api("/v1/proof", {
      method: "POST",
      body: JSON.stringify({
        title: els.title.value.trim() || "Untitled",
        text,
        document_key: els.documentKey.value.trim() || null,
        format: els.format.value,
        seed: els.seed.value.trim() || "proof",
        budget_seconds: 60,
        actor_id: actorId(),
      }),
    });
    renderReceipt(receipt);
    setRunState("done", "done");
    setProofButtons({ disabled: true, state: "success", label: "Done" });
    const n = (receipt.shots || []).length;
    const claim = receipt.claim || "controlled_proof_not_production_ready";
    showAlert(
      `Proof finished · ${n} shot(s) · claim ${claim} · download the receipt below`,
      "ok",
    );
    $("receipt")?.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    setStep(2);
    setRunState("error", "error");
    setProofButtons({ disabled: true, state: "error", label: "Failed" });
    const msg = err instanceof Error ? err.message : String(err);
    showAlert(
      msg.includes("Failed to fetch") || msg.includes("NetworkError")
        ? "Cannot reach the API. Is the server running on this host?"
        : msg,
    );
  } finally {
    window.setTimeout(() => {
      setProofButtons({ disabled: false, state: "", label: "Run proof" });
    }, 900);
  }
}

async function compileOnly() {
  showAlert("");
  const text = els.script.value.trim();
  if (!text) {
    showAlert("Script source is empty.");
    return;
  }
  els.btnCompile.disabled = true;
  try {
    const doc = await api("/v1/compile", {
      method: "POST",
      body: JSON.stringify({
        title: els.title.value.trim() || "Untitled",
        text,
        document_key: els.documentKey.value.trim() || null,
        format: els.format.value,
      }),
    });
    lastCompiledDocument = doc;
    const scenes = (doc.scenes || []).length;
    const coverage = doc.coverage?.ratio;
    const diags = (doc.diagnostics || []).length;
    showAlert(
      `Compile ok · ${scenes} scene(s)` +
        (coverage != null ? ` · coverage ${coverage}` : "") +
        (diags ? ` · ${diags} diagnostic(s)` : "") +
        ` · full path (default)`,
      diags ? "error" : "ok",
    );
  } catch (err) {
    showAlert(err instanceof Error ? err.message : String(err));
  } finally {
    els.btnCompile.disabled = false;
  }
}

async function compileIncremental() {
  showAlert("");
  const text = els.script.value.trim();
  if (!text) {
    showAlert("Script source is empty.");
    return;
  }
  if (els.btnCompileIncremental) els.btnCompileIncremental.disabled = true;
  try {
    const body = {
      title: els.title.value.trim() || "Untitled",
      text,
      document_key: els.documentKey.value.trim() || null,
      format: els.format.value,
    };
    if (lastCompiledDocument) {
      body.prior_document = lastCompiledDocument;
    }
    const payload = await api("/v1/compile/incremental", {
      method: "POST",
      body: JSON.stringify(body),
    });
    if (payload.document) {
      lastCompiledDocument = payload.document;
    }
    const ids = payload.stale_shot_ids || [];
    tableView.staleShotIds = new Set(ids.map(String));
    if (lastReceipt) renderShotTable();
    const carried = (payload.carried_scene_ids || []).length;
    const recompiled = (payload.recompiled_scene_ids || []).length;
    const added = (payload.added_scene_ids || []).length;
    const covOk =
      payload.coverage_accounted_characters ===
      payload.coverage_source_characters;
    showAlert(
      `Incremental compile · carried ${carried} · recompiled ${recompiled}` +
        (added ? ` · added ${added}` : "") +
        ` · stale shots ${ids.length}` +
        (covOk ? " · coverage full partition" : " · coverage mismatch") +
        " · not production film · PROPOSED not elevated",
      covOk ? "ok" : "error",
    );
  } catch (err) {
    showAlert(err instanceof Error ? err.message : String(err));
  } finally {
    if (els.btnCompileIncremental) els.btnCompileIncremental.disabled = false;
  }
}

async function loadProjectStatus() {
  const key = activeDocumentKey();
  if (!key) {
    showAlert("Set a Project ID under Script options first.");
    return;
  }
  const status = await api(`/v1/projects/${encodeURIComponent(key)}/status`);
  renderStatus(status);
  showAlert(`Status loaded · ${status.document_key}`, "ok");
}

async function listProjects() {
  const payload = await api("/v1/projects");
  renderProjectList(payload);
  showAlert(
    `Projects · tenant ${payload.tenant_id} · count ${(payload.projects || []).length}`,
    "ok",
  );
}

function downloadText(filename, text, mime) {
  const blob = new Blob([text], { type: mime || "text/plain" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

function exportStem() {
  const key =
    lastBreakdown?.document_key ||
    lastReceipt?.document_key ||
    els.documentKey?.value ||
    "breakdown";
  return String(key)
    .replaceAll("::", "__")
    .replaceAll(/[^\w.-]+/g, "_");
}

function exportReceipt() {
  if (!lastReceipt) {
    showAlert("Run a proof first, then download the receipt.");
    return;
  }
  const name = `${exportStem()}.proof-receipt.json`;
  downloadText(name, JSON.stringify(lastReceipt, null, 2), "application/json");
  showAlert(`Downloaded ${name}`, "ok");
}

function exportBreakdownJson() {
  if (!lastBreakdown) {
    showAlert("Build a breakdown first, then download JSON.");
    return;
  }
  const name = `${exportStem()}.breakdown.json`;
  downloadText(name, JSON.stringify(lastBreakdown, null, 2), "application/json");
  showAlert(`Downloaded ${name} · connector-ready · not production film`, "ok");
}

function exportBreakdownMarkdown() {
  if (!lastBreakdownMarkdown && !lastBreakdown) {
    showAlert("Build a breakdown first, then download Markdown.");
    return;
  }
  const body =
    lastBreakdownMarkdown ||
    JSON.stringify(lastBreakdown, null, 2);
  const name = `${exportStem()}.breakdown.md`;
  downloadText(name, body, "text/markdown");
  showAlert(`Downloaded ${name}`, "ok");
}

/**
 * Map breakdown package into the shot table (no mock media / proof required).
 */
function renderBreakdown(package) {
  lastBreakdown = package;
  els.receiptEmpty.hidden = true;
  els.receiptBody.hidden = false;
  els.runMeta.hidden = false;
  setStep(3);

  if (els.receiptExec) {
    els.receiptExec.textContent = "breakdown ok";
    els.receiptExec.className = "chip chip--ok";
  }
  if (els.receiptBudget) {
    els.receiptBudget.hidden = true;
  }
  if (els.receiptClaim) {
    els.receiptClaim.hidden = false;
    els.receiptClaim.textContent = "not production film";
    els.receiptClaim.className = "chip chip--warn";
  }
  if (els.resultStack) els.resultStack.hidden = false;
  if (els.resultBanner) {
    els.resultBanner.hidden = false;
    els.resultBanner.textContent =
      `Breakdown · ${package.shot_count || 0} shots · ` +
      `${package.entity_count || 0} entities · connector-ready JSON`;
    els.resultBanner.className = "result-banner result-banner--exec";
  }
  if (els.claimPostProof) els.claimPostProof.hidden = false;
  if (els.claimExecLabel) {
    setText(
      els.claimExecLabel,
      `${package.scene_count || 0} scenes · ${package.shot_count || 0} shots`,
    );
  }
  if (els.claimBudgetLabel) {
    setText(els.claimBudgetLabel, "n/a (no media generation)");
  }
  if (els.rClaimCode) {
    els.rClaimCode.textContent =
      package.claim || "shot_breakdown_with_continuity_not_production_film";
  }

  setText(els.rClaim, package.claim || "—");
  setText(els.rDoc, package.document_key || "—");
  setText(els.rHash, package.package_hash || "—");
  setText(els.rSchema, package.schema_version || "cf.breakdown.v1");
  setText(els.rSource, package.source_hash || "—");
  setText(els.rIr, package.production_ir_hash || "—");
  setText(els.rLedger, package.ledger_hash || "—");
  setText(els.rShotsHash, package.shot_contracts_hash || "—");

  setText(els.metaElapsed, "—");
  setText(els.metaBudget, "—");
  setText(els.metaWithin, "—");
  setText(els.metaShots, String(package.shot_count || 0));
  if (els.metaCost) setText(els.metaCost, "—");
  if (els.costPanel) els.costPanel.hidden = true;

  // Shape shots for existing table (status = breakdown; no repair media)
  const shots = (package.shots || []).map((s) => ({
    shot_id: s.shot_id,
    scene_id: s.scene_id,
    label: s.label || s.slugline,
    status: "breakdown",
    attempts: 0,
    accepted_candidate_hash: null,
    repair_actions: [],
    repair_rationale: s.constraints?.length
      ? s.constraints
          .map((c) => c.description || c.code)
          .filter(Boolean)
          .slice(0, 3)
          .join("; ")
      : s.characters_present?.length
        ? `cast: ${s.characters_present.join(", ")}`
        : null,
    _breakdown: s,
  }));

  // Synthetic receipt-like object so table helpers work
  lastReceipt = {
    claim: package.claim,
    document_key: package.document_key,
    receipt_hash: package.package_hash,
    schema_version: package.schema_version,
    source_hash: package.source_hash,
    production_ir_hash: package.production_ir_hash,
    ledger_hash: package.ledger_hash,
    shot_contracts_hash: package.shot_contracts_hash,
    shots,
    _kind: "breakdown",
  };

  buildSceneIndex(shots);
  nav.focusSceneId = null;
  nav.focusShotIndex = 0;
  applyNavFromUrl();
  renderSceneNav();
  renderShotTable();
  syncNavUrl();

  els.rawJson.textContent = JSON.stringify(package, null, 2);
}

function stemFromFilename(name) {
  const base = String(name || "script").split(/[/\\]/).pop() || "script";
  return base.replace(/\.(fountain|fdx|txt)$/i, "") || "script";
}

function importScriptFile(file) {
  if (!file) return;
  const name = file.name || "script.fountain";
  const lower = name.toLowerCase();
  const isFdx = lower.endsWith(".fdx");
  const reader = new FileReader();
  reader.onload = () => {
    const text = String(reader.result || "");
    if (!text.trim()) {
      showAlert("Imported file is empty.");
      return;
    }
    els.script.value = text;
    if (els.format) els.format.value = isFdx ? "fdx" : "fountain";
    const stem = stemFromFilename(name);
    if (els.title && (!els.title.value || els.title.value === "Continuity Sample")) {
      els.title.value = stem;
    }
    if (els.documentKey && (!els.documentKey.value || els.documentKey.value === "continuity")) {
      els.documentKey.value = stem.replaceAll(/[^\w.-]+/g, "-").toLowerCase();
    }
    showAlert(
      `Imported ${name} · format ${isFdx ? "FDX" : "Fountain"} · click Build breakdown`,
      "ok",
    );
  };
  reader.onerror = () => showAlert("Could not read the selected file.");
  reader.readAsText(file);
}

async function buildBreakdown() {
  showAlert("");
  const text = els.script.value.trim();
  if (!text) {
    showAlert("Paste a screenplay or use Import file first.");
    return;
  }
  setBreakdownButtons({
    disabled: true,
    state: "running",
    label: "Building…",
  });
  try {
    const body = {
      title: els.title.value.trim() || "Untitled",
      text,
      document_key: els.documentKey.value.trim() || null,
      format: els.format.value,
    };
    const package = await api("/v1/breakdown", {
      method: "POST",
      body: JSON.stringify(body),
    });
    let markdown = null;
    try {
      const mdPayload = await api("/v1/breakdown/markdown", {
        method: "POST",
        body: JSON.stringify(body),
      });
      markdown = mdPayload.markdown || null;
    } catch {
      markdown = null;
    }
    lastBreakdownMarkdown = markdown;
    renderBreakdown(package);
    setRunState("done", "breakdown ready");
    showAlert(
      `Breakdown ready · ${package.shot_count} shot(s) · ` +
        `${package.entity_count} entit(y/ies) · download JSON for connectors · not production film`,
      "ok",
    );
  } catch (err) {
    setRunState("error", "failed");
    showAlert(err instanceof Error ? err.message : String(err));
  } finally {
    setBreakdownButtons({
      disabled: false,
      state: "",
      label: "Build breakdown",
    });
  }
}

async function copyReceiptHash() {
  if (!lastReceipt?.receipt_hash) {
    showAlert("No receipt hash to copy.");
    return;
  }
  try {
    await navigator.clipboard.writeText(String(lastReceipt.receipt_hash));
    showAlert("Receipt hash copied.", "ok");
  } catch {
    showAlert("Clipboard unavailable — copy from the receipt panel.");
  }
}

async function bootstrapDevKey() {
  showAlert("");
  try {
    const data = await api("/v1/tenants/bootstrap-dev", { method: "POST" });
    if (data.api_key) {
      els.apiKey.value = data.api_key;
      persistPrefs();
    }
    await pingWhoami();
    showAlert(
      `Dev tenant ${data.tenant_id} · key stored in field (localStorage)`,
      "ok",
    );
  } catch (err) {
    showAlert(err instanceof Error ? err.message : String(err));
  }
}

function loadSample() {
  els.script.value = SAMPLE_SCRIPT;
  els.documentKey.value = "continuity";
  els.title.value = "Continuity Sample";
  els.format.value = "fountain";
  els.seed.value = "proof";
  setStep(1);
  setRunState("idle", "ready");
  showAlert("Sample script loaded — click Run proof.", "ok");
}

function clearScript() {
  els.script.value = "";
  setStep(1);
  setRunState("idle", "ready");
  showAlert("Script cleared.");
  els.script?.focus();
}

function wireStickyCta() {
  const primary = els.btnBreakdown || $("btn-breakdown") || $("btn-proof");
  if (!els.stickyCta || !primary) return;
  const io = new IntersectionObserver(
    ([entry]) => {
      els.stickyCta.classList.toggle("is-visible", !entry.isIntersecting);
    },
    { threshold: 0.2 },
  );
  io.observe(primary);
}

function restorePrefs() {
  try {
    const base = localStorage.getItem("cf.apiBase");
    const key = localStorage.getItem("cf.apiKey");
    if (base) els.apiBase.value = base;
    if (key) els.apiKey.value = key;
  } catch {
    /* ignore */
  }
}

function persistPrefs() {
  try {
    localStorage.setItem("cf.apiBase", els.apiBase.value.trim());
    localStorage.setItem("cf.apiKey", els.apiKey.value.trim());
  } catch {
    /* ignore */
  }
}

function wire() {
  restorePrefs();
  els.script.value = SAMPLE_SCRIPT;
  setStep(1);
  setRunState("idle", "ready");
  wireStickyCta();
  applyNavFromUrl();

  els.btnSceneAll?.addEventListener("click", () => setSceneFocus(null));
  els.btnScenePrev?.addEventListener("click", () => stepScene(-1));
  els.btnSceneNext?.addEventListener("click", () => stepScene(1));
  els.btnStalePreview?.addEventListener("click", () => {
    previewStaleForFocus().catch((err) =>
      showAlert(err instanceof Error ? err.message : String(err)),
    );
  });
  els.btnStaleClear?.addEventListener("click", clearStaleMarks);

  const onTableControls = () => {
    if (els.shotFilterStatus) {
      tableView.statusFilter = els.shotFilterStatus.value || "all";
    }
    if (els.shotFilterRepair) {
      tableView.repairFilter = els.shotFilterRepair.value || "all";
    }
    if (els.shotSort) {
      tableView.sort = els.shotSort.value || "default";
    }
    if (els.shotVirtual) {
      tableView.virtualEnabled = !!els.shotVirtual.checked;
    }
    nav.focusShotIndex = 0;
    renderShotTable();
    syncNavUrl();
  };
  els.shotFilterStatus?.addEventListener("change", onTableControls);
  els.shotFilterRepair?.addEventListener("change", onTableControls);
  els.shotSort?.addEventListener("change", onTableControls);
  els.shotVirtual?.addEventListener("change", onTableControls);

  document.addEventListener("keydown", (ev) => {
    // Skip when typing in fields
    const tag = (ev.target && /** @type {HTMLElement} */ (ev.target).tagName) || "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    if (!lastReceipt) return;
    if (ev.key === "[") {
      ev.preventDefault();
      stepScene(-1);
    } else if (ev.key === "]") {
      ev.preventDefault();
      stepScene(1);
    } else if (ev.key === "ArrowLeft") {
      ev.preventDefault();
      stepShot(-1);
    } else if (ev.key === "ArrowRight") {
      ev.preventDefault();
      stepShot(1);
    }
  });

  if (els.btnBreakdown) {
    els.btnBreakdown.addEventListener("click", () => {
      buildBreakdown().catch((err) =>
        showAlert(err instanceof Error ? err.message : String(err)),
      );
    });
  }
  if (els.btnImport && els.scriptFile) {
    els.btnImport.addEventListener("click", () => els.scriptFile.click());
    els.scriptFile.addEventListener("change", () => {
      const file = els.scriptFile.files && els.scriptFile.files[0];
      importScriptFile(file);
      els.scriptFile.value = "";
    });
  }
  // Drag-and-drop import onto the script field
  if (els.script) {
    els.script.addEventListener("dragover", (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
    });
    els.script.addEventListener("drop", (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
      const file = ev.dataTransfer?.files?.[0];
      if (file) importScriptFile(file);
    });
  }
  els.btnProof.addEventListener("click", runProof);
  if (els.btnBreakdownSticky) {
    els.btnBreakdownSticky.addEventListener("click", () => {
      buildBreakdown().catch((err) =>
        showAlert(err instanceof Error ? err.message : String(err)),
      );
    });
  }
  els.btnHealth.addEventListener("click", async () => {
    showAlert("");
    try {
      const data = await pingHealth();
      await pingWhoami();
      showAlert(`API ok · ${data.backend} · v${data.version}`, "ok");
    } catch (err) {
      showAlert(
        err instanceof Error
          ? `API offline: ${err.message}`
          : "API offline",
      );
    }
  });
  els.btnCompile.addEventListener("click", compileOnly);
  if (els.btnCompileIncremental) {
    els.btnCompileIncremental.addEventListener("click", () => {
      compileIncremental().catch((err) =>
        showAlert(err instanceof Error ? err.message : String(err)),
      );
    });
  }
  els.btnSample.addEventListener("click", loadSample);
  els.btnClear.addEventListener("click", clearScript);
  els.btnBootstrap.addEventListener("click", bootstrapDevKey);
  els.btnWhoami.addEventListener("click", async () => {
    showAlert("");
    try {
      const data = await pingWhoami();
      if (!data) {
        showAlert("Could not identify you — set an API key if auth is required.");
        return;
      }
      showAlert(`Signed in · tenant ${data.tenant_id} · actor ${data.actor_id}`, "ok");
    } catch (err) {
      showAlert(err instanceof Error ? err.message : String(err));
    }
  });
  els.btnExport.addEventListener("click", exportReceipt);
  if (els.btnExportBreakdown) {
    els.btnExportBreakdown.addEventListener("click", exportBreakdownJson);
  }
  if (els.btnExportBreakdownMd) {
    els.btnExportBreakdownMd.addEventListener("click", exportBreakdownMarkdown);
  }
  els.btnCopyHash.addEventListener("click", () => {
    copyReceiptHash().catch((err) =>
      showAlert(err instanceof Error ? err.message : String(err)),
    );
  });
  els.btnStatus.addEventListener("click", () => {
    loadProjectStatus().catch((err) =>
      showAlert(err instanceof Error ? err.message : String(err)),
    );
  });
  els.btnList.addEventListener("click", () => {
    listProjects().catch((err) =>
      showAlert(err instanceof Error ? err.message : String(err)),
    );
  });
  els.btnLeaseAcquire.addEventListener("click", () => {
    acquireLease().catch((err) =>
      showAlert(err instanceof Error ? err.message : String(err)),
    );
  });
  els.btnLeaseRelease.addEventListener("click", () => {
    releaseLease().catch((err) =>
      showAlert(err instanceof Error ? err.message : String(err)),
    );
  });
  els.btnLeaseRefresh.addEventListener("click", () => {
    refreshLease()
      .then((p) =>
        showAlert(p.active ? "Lease active" : "No active lease", "ok"),
      )
      .catch((err) => showAlert(err instanceof Error ? err.message : String(err)));
  });
  els.btnApprovalRequest.addEventListener("click", () => {
    requestApproval().catch((err) =>
      showAlert(err instanceof Error ? err.message : String(err)),
    );
  });
  els.btnApprovalsList.addEventListener("click", () => {
    listApprovals().catch((err) =>
      showAlert(err instanceof Error ? err.message : String(err)),
    );
  });
  els.btnRunsList.addEventListener("click", () => {
    listRuns().catch((err) =>
      showAlert(err instanceof Error ? err.message : String(err)),
    );
  });
  els.apiBase.addEventListener("change", persistPrefs);
  els.apiKey.addEventListener("change", persistPrefs);

  document.addEventListener("keydown", (ev) => {
    if ((ev.metaKey || ev.ctrlKey) && ev.key === "Enter") {
      ev.preventDefault();
      // Primary handoff path: build breakdown (not mock proof)
      if (els.btnBreakdown && !els.btnBreakdown.disabled) {
        buildBreakdown().catch((err) =>
          showAlert(err instanceof Error ? err.message : String(err)),
        );
      }
    }
  });

  Promise.all([pingHealth(), pingWhoami()]).catch(() => {
    /* offline until API is up */
  });
}

wire();
