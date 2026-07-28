/**
 * Continuity Forge · Proof Workbench
 * Primary action: POST /v1/proof → render receipt.
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
  btnSample: $("btn-sample"),
  btnClear: $("btn-clear"),
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
};

function baseUrl() {
  const raw = (els.apiBase.value || "").trim().replace(/\/$/, "");
  return raw;
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

function renderReceipt(receipt) {
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

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
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
      showAlert(`health ok · backend ${data.backend} · v${data.version}`, "ok");
    } catch (err) {
      showAlert(err instanceof Error ? err.message : String(err));
    }
  });
  els.btnSample.addEventListener("click", loadSample);
  els.btnClear.addEventListener("click", clearScript);
  els.apiBase.addEventListener("change", persistPrefs);
  els.apiKey.addEventListener("change", persistPrefs);

  // Keyboard: Cmd/Ctrl+Enter runs proof
  document.addEventListener("keydown", (ev) => {
    if ((ev.metaKey || ev.ctrlKey) && ev.key === "Enter") {
      ev.preventDefault();
      if (!els.btnProof.disabled) runProof();
    }
  });

  pingHealth().catch(() => {
    /* offline until API is up */
  });
}

wire();
