/**
 * Continuity Forge · Proof Workbench v1.2
 * Primary: POST /v1/proof → receipt. Secondary: canon status, export, auth bootstrap.
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

const els = {
  script: $("script"),
  documentKey: $("document-key"),
  title: $("title"),
  format: $("format"),
  seed: $("seed"),
  apiBase: $("api-base"),
  apiKey: $("api-key"),
  btnProof: $("btn-proof"),
  btnHealth: $("btn-health"),
  btnCompile: $("btn-compile"),
  btnSample: $("btn-sample"),
  btnClear: $("btn-clear"),
  btnBootstrap: $("btn-bootstrap"),
  btnWhoami: $("btn-whoami"),
  btnExport: $("btn-export"),
  btnCopyHash: $("btn-copy-hash"),
  btnStatus: $("btn-status"),
  btnList: $("btn-list"),
  runState: $("run-state"),
  runMeta: $("run-meta"),
  metaElapsed: $("meta-elapsed"),
  metaBudget: $("meta-budget"),
  metaWithin: $("meta-within"),
  metaShots: $("meta-shots"),
  alert: $("alert"),
  chipHealth: $("chip-health"),
  chipBackend: $("chip-backend"),
  chipVersion: $("chip-version"),
  chipTenant: $("chip-tenant"),
  receiptEmpty: $("receipt-empty"),
  receiptBody: $("receipt-body"),
  receiptClaim: $("receipt-claim"),
  rClaim: $("r-claim"),
  rDoc: $("r-doc"),
  rHash: $("r-hash"),
  rSchema: $("r-schema"),
  rSource: $("r-source"),
  rIr: $("r-ir"),
  rLedger: $("r-ledger"),
  rShotsHash: $("r-shots-hash"),
  shotRows: $("shot-rows"),
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
  els.runState.dataset.state = state;
  els.runState.textContent = label;
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
    els.chipHealth.textContent = `health · ${data.status || "ok"}`;
    els.chipHealth.className = "chip chip--ok";
    els.chipBackend.textContent = `backend · ${data.backend || "—"}`;
    els.chipVersion.textContent = `api · ${data.version || "—"}`;
    return data;
  } catch (err) {
    els.chipHealth.textContent = "health · unreachable";
    els.chipHealth.className = "chip chip--danger";
    els.chipBackend.textContent = "backend · —";
    els.chipVersion.textContent = "api · —";
    throw err;
  }
}

async function pingWhoami() {
  try {
    const data = await api("/v1/whoami");
    els.chipTenant.textContent = `tenant · ${data.tenant_id || "—"}`;
    els.chipTenant.className = "chip chip--accent";
    return data;
  } catch {
    els.chipTenant.textContent = "tenant · —";
    els.chipTenant.className = "chip";
    return null;
  }
}

function renderReceipt(receipt) {
  lastReceipt = receipt;
  els.receiptEmpty.hidden = true;
  els.receiptBody.hidden = false;
  els.runMeta.hidden = false;

  const claim = receipt.claim || "controlled_proof_not_production_ready";
  els.receiptClaim.textContent = claim;
  els.receiptClaim.className = "chip chip--warn";

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
      ? `${receipt.elapsed_seconds.toFixed(4)} s`
      : "—";
  setText(els.metaElapsed, elapsed);
  setText(
    els.metaBudget,
    receipt.budget_seconds != null ? `${receipt.budget_seconds} s` : "—",
  );
  setText(
    els.metaWithin,
    receipt.within_budget === true
      ? "true"
      : receipt.within_budget === false
        ? "false"
        : "—",
  );
  setText(els.metaShots, String((receipt.shots || []).length));

  els.shotRows.replaceChildren();
  for (const shot of receipt.shots || []) {
    const tr = document.createElement("tr");
    const status = shot.status || "";
    const statusClass =
      status.includes("accept") || status === "accepted_proposed"
        ? "status-ok"
        : status.includes("fail") || status.includes("reject")
          ? "status-fail"
          : "";
    const repairs = (shot.repair_actions || []).join(", ") || "—";
    tr.innerHTML = `
      <td>${escapeHtml(shot.label || shortHash(shot.shot_id))}</td>
      <td class="${statusClass}">${escapeHtml(status)}</td>
      <td>${escapeHtml(String(shot.attempts ?? "—"))}</td>
      <td>${escapeHtml(repairs)}</td>
      <td title="${escapeHtml(shot.accepted_candidate_hash || "")}">${escapeHtml(
        shortHash(shot.accepted_candidate_hash),
      )}</td>
    `;
    els.shotRows.appendChild(tr);
  }

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
    showAlert("Script source is empty.");
    return;
  }

  els.btnProof.disabled = true;
  els.btnProof.dataset.state = "loading";
  els.btnProof.textContent = "Running…";
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
        actor_id: "proof-ui",
      }),
    });
    renderReceipt(receipt);
    setRunState("done", "done");
    els.btnProof.dataset.state = "success";
    els.btnProof.textContent = "Proof complete";
    showAlert(
      `Receipt ${shortHash(receipt.receipt_hash)} · claim ${receipt.claim}`,
      "ok",
    );
    $("receipt")?.scrollIntoView({ behavior: "smooth", block: "start" });
    // Best-effort canon refresh (tenant key already in store).
    loadProjectStatus().catch(() => {
      /* status optional after proof */
    });
    listProjects().catch(() => {
      /* list optional */
    });
  } catch (err) {
    setRunState("error", "error");
    els.btnProof.dataset.state = "error";
    els.btnProof.textContent = "Proof failed";
    showAlert(err instanceof Error ? err.message : String(err));
  } finally {
    window.setTimeout(() => {
      els.btnProof.disabled = false;
      els.btnProof.dataset.state = "";
      els.btnProof.textContent = "Run controlled proof";
    }, 1200);
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
    const scenes = (doc.scenes || []).length;
    const coverage = doc.coverage?.ratio;
    const diags = (doc.diagnostics || []).length;
    showAlert(
      `Compile ok · ${scenes} scene(s)` +
        (coverage != null ? ` · coverage ${coverage}` : "") +
        (diags ? ` · ${diags} diagnostic(s)` : ""),
      diags ? "error" : "ok",
    );
  } catch (err) {
    showAlert(err instanceof Error ? err.message : String(err));
  } finally {
    els.btnCompile.disabled = false;
  }
}

async function loadProjectStatus() {
  const key = activeDocumentKey();
  if (!key) {
    showAlert("Set document_key first.");
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

function exportReceipt() {
  if (!lastReceipt) {
    showAlert("No receipt to export.");
    return;
  }
  const blob = new Blob([JSON.stringify(lastReceipt, null, 2)], {
    type: "application/json",
  });
  const stem = String(lastReceipt.document_key || "proof")
    .replaceAll("::", "__")
    .replaceAll(/[^\w.-]+/g, "_");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${stem}.proof-receipt.json`;
  a.click();
  URL.revokeObjectURL(a.href);
  showAlert(`Exported ${a.download}`, "ok");
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
  showAlert("");
}

function clearScript() {
  els.script.value = "";
  showAlert("");
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
  loadSample();

  els.btnProof.addEventListener("click", runProof);
  els.btnHealth.addEventListener("click", async () => {
    showAlert("");
    try {
      const data = await pingHealth();
      await pingWhoami();
      showAlert(`health ok · backend ${data.backend} · v${data.version}`, "ok");
    } catch (err) {
      showAlert(err instanceof Error ? err.message : String(err));
    }
  });
  els.btnCompile.addEventListener("click", compileOnly);
  els.btnSample.addEventListener("click", loadSample);
  els.btnClear.addEventListener("click", clearScript);
  els.btnBootstrap.addEventListener("click", bootstrapDevKey);
  els.btnWhoami.addEventListener("click", async () => {
    showAlert("");
    try {
      const data = await pingWhoami();
      if (!data) {
        showAlert("whoami failed — set API key if auth is required.");
        return;
      }
      showAlert(
        `whoami · tenant ${data.tenant_id} · actor ${data.actor_id}`,
        "ok",
      );
    } catch (err) {
      showAlert(err instanceof Error ? err.message : String(err));
    }
  });
  els.btnExport.addEventListener("click", exportReceipt);
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
  els.apiBase.addEventListener("change", persistPrefs);
  els.apiKey.addEventListener("change", persistPrefs);

  document.addEventListener("keydown", (ev) => {
    if ((ev.metaKey || ev.ctrlKey) && ev.key === "Enter") {
      ev.preventDefault();
      if (!els.btnProof.disabled) runProof();
    }
  });

  Promise.all([pingHealth(), pingWhoami()]).catch(() => {
    /* offline until API is up */
  });
}

wire();
