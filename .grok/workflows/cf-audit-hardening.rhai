// Continuity Forge Engineering + UI Audit → campaign workflow
// Encodes the audit phases: plan (default) or execute phase 1–4.
// Does NOT rewrite architecture; hardens verification, CI, authority, UX.

let meta = #{
    name: "cf-audit-hardening",
    description: "Execute Continuity Forge engineering+UI audit: plan campaign or implement trust-boundary, production CI, operator UX, long-form readiness phases",
    when_to_use: "After Continuity Forge audit; verification debt, production CI, authority invariants, operator UX upgrade, /cf-audit-hardening",
    phases: [
        #{ title: "Baseline", detail: "re-ground audit claims against the live tree" },
        #{ title: "Campaign", detail: "synthesize prioritized PR plan" },
        #{ title: "Execute", detail: "optional implement + verify a selected phase" },
        #{ title: "Report", detail: "write campaign receipt" },
    ],
};

// --- args ---
// mode: "plan" (default) | "execute"
// phase: "1" | "2" | "3" | "4" | "all"  (execute only; default "1")
// root: optional repo path hint for agents

let mode = "plan";
let phase_sel = "1";
let root_hint = "continuity-forge repo (main)";

if args != () {
    if args.mode != () {
        mode = args.mode;
        mode = mode.to_string();
    }
    if args.phase != () {
        phase_sel = args.phase;
        phase_sel = phase_sel.to_string();
    }
    if args.root != () {
        root_hint = args.root;
        root_hint = root_hint.to_string();
    }
}

if mode != "plan" && mode != "execute" {
    pause("verification", "args.mode must be plan or execute");
}

// ========== BASELINE (always) ==========
phase("Baseline");
log("Baseline re-ground of audit claims against " + root_hint);

let base_prompt_prefix = "";
base_prompt_prefix += "You are auditing Continuity Forge at workspace root. ";
base_prompt_prefix += "Use read-only tools only: list_dir, read_file, grep, run_terminal_command for git status/diff if needed. ";
base_prompt_prefix += "Do not answer from memory — open real files. ";
base_prompt_prefix += "Repo context: Python monorepo, packages/*, apps/api, apps/mcp, apps/web, deploy/, scripts/validate_m0.py, .github/workflows/ci.yml. ";
base_prompt_prefix += "Root hint: " + root_hint + ". ";

let jobs = [];

let p_ci = base_prompt_prefix;
p_ci += "Focus: CI/CD maturity. Read .github/workflows/ci.yml, scripts/validate_m0.py, pyproject.toml, deploy/smoke.sh, Makefile. ";
p_ci += "Confirm whether production extras, Docker smoke, Postgres/MinIO/Temporal, wheel install, multi-Python matrix are in the merge gate. ";
p_ci += "Return markdown: ## CI baseline with OBSERVED bullets and gap list mapped to Fast/Packaging/Integration/Production-stack gates.";
jobs.push(#{ prompt: p_ci, label: "baseline-ci", capability_mode: "read-only" });

let p_auth = base_prompt_prefix;
p_auth += "Focus: authority boundaries and mutation contract. Read AGENTS.md, packages/operator (MutationEnvelope, ProjectStore), apps/api main.py, apps/mcp server.py, packages/providers, packages/runtime. ";
p_auth += "Check whether every write path requires envelope fields; whether providers import persistence; whether architecture tests enforce dependency edges. ";
p_auth += "Return markdown: ## Authority baseline with OBSERVED/INFERRED and concrete file:line citations.";
jobs.push(#{ prompt: p_auth, label: "baseline-authority", capability_mode: "read-only" });

let p_ui = base_prompt_prefix;
p_ui += "Focus: operator UI information architecture. Read apps/web/index.html, apps/web/app.js, apps/web/styles.css, docs/campaigns/CONTINUITY_FORGE_OPERATOR_UI_001.md. ";
p_ui += "Assess progressive disclosure, separation of execution success vs readiness, approval queues, revision-impact views, a11y baseline. ";
p_ui += "Return markdown: ## UI baseline with what is prototype-quality vs missing for long-form production.";
jobs.push(#{ prompt: p_ui, label: "baseline-ui", capability_mode: "read-only" });

let p_test = base_prompt_prefix;
p_test += "Focus: testing and verification debt. Read tests/ tree, pytest config in pyproject.toml, coverage usage in validate_m0.py. ";
p_test += "Note missing: coverage floors, concurrency/lease tests, failure-injection, property tests, Temporal resume. ";
p_test += "Return markdown: ## Verification baseline with prioritized missing test classes.";
jobs.push(#{ prompt: p_test, label: "baseline-tests", capability_mode: "read-only" });

let baseline = parallel(jobs);

let baseline_md = "# Continuity Forge — audit baseline (workflow)\n\n";
let bi = 0;
for r in baseline {
    let title = "panel-" + bi.to_string();
    if bi == 0 { title = "CI"; }
    if bi == 1 { title = "Authority"; }
    if bi == 2 { title = "UI"; }
    if bi == 3 { title = "Tests"; }
    if r == () || !r.success {
        baseline_md += "## " + title + "\n\n_Baseline agent failed or empty — treat claims as unverified._\n\n";
    } else {
        baseline_md += "## " + title + "\n\n";
        baseline_md += r.output.to_string();
        baseline_md += "\n\n";
    }
    bi += 1;
}

// ========== CAMPAIGN PLAN ==========
phase("Campaign");

let plan_prompt = "";
plan_prompt += "Synthesize an executable engineering campaign for Continuity Forge from this baseline report. ";
plan_prompt += "Do not invent greenfield architecture rewrites. architecture_rewrite is NOT_REQUIRED. ";
plan_prompt += "Respect priority: (1) executable authority invariants (2) production-stack CI (3) failure recovery (4) decision-oriented continuity review UI. ";
plan_prompt += "Defer frontend framework migration. ";
plan_prompt += "Write a full markdown campaign plan with: executive summary, phase 1-4 work breakdown (PR-sized slices), acceptance criteria per slice, test plan, risks, and what NOT to do. ";
plan_prompt += "Phase definitions from the audit:\n";
plan_prompt += "Phase 1 Trust boundary: mutation envelope universality, architecture dependency tests, state transitions, expected-state conflicts, lease concurrency, tenant isolation, bootstrap-route safety.\n";
plan_prompt += "Phase 2 Production validation: wheel-install CI, Postgres+MinIO jobs, Temporal interrupt/resume, docker smoke in CI, critical-module coverage thresholds, failure injection, rename validate_m0 to durable name.\n";
plan_prompt += "Phase 3 Operator UX: separate execution success from readiness, validator evidence + repair rationale, approval/waiver queues, revision-impact and stale-artifact views (no React migration).\n";
plan_prompt += "Phase 4 Long-form: scene/shot navigation, virtualized tables, dependency-graph invalidation, incremental compile, budget/provider telemetry, streaming workflow state.\n";
plan_prompt += "\nBASELINE REPORT:\n";
plan_prompt += baseline_md;
plan_prompt += "\nUse tools only if you need to confirm a path; prefer synthesizing from the baseline. ";
plan_prompt += "Output the campaign markdown only.";

let plan_agent = agent(plan_prompt, #{
    label: "campaign-plan",
    capability_mode: "read-only",
});

let campaign_md = "# Campaign plan unavailable\n";
if plan_agent != () && plan_agent.success {
    campaign_md = plan_agent.output.to_string();
}

let plan_path = write_scratch_file("cf-audit-campaign-plan.md", campaign_md);
log("Campaign plan written: " + plan_path);

if mode == "plan" {
    phase("Report");
    let report = "";
    report += "# Continuity Forge audit-hardening — PLAN receipt\n\n";
    report += "Mode: plan (no code changes).\n\n";
    report += "Baseline panels: CI, Authority, UI, Tests.\n\n";
    report += "Campaign plan artifact: " + plan_path + "\n\n";
    report += "Next: run with args `{ \"mode\": \"execute\", \"phase\": \"1\" }` to implement Phase 1 trust-boundary hardening.\n\n";
    report += "Phases: 1 trust-boundary · 2 production-CI · 3 operator-UX · 4 long-form (defer until 1–3 land).\n\n";
    report += "---\n\n";
    report += campaign_md;
    let rpath = write_scratch_file("cf-audit-report.md", report);
    complete(#{
        summary: "Plan complete — campaign plan ready; no code changes",
        mode: "plan",
        plan_path: plan_path,
        report_path: rpath,
        next: "execute phase 1",
    });
}

// ========== EXECUTE ==========
phase("Execute");
log("Execute mode phase=" + phase_sel);

if phase_sel != "1" && phase_sel != "2" && phase_sel != "3" && phase_sel != "4" && phase_sel != "all" {
    pause("verification", "args.phase must be 1, 2, 3, 4, or all");
}

// Run selected phases (all => 1 then await, etc. via sequential blocks)
let executed = [];
let verify_notes = [];

// --- Phase 1 ---
if phase_sel == "1" || phase_sel == "all" {
    log("Phase 1: trust boundary hardening");
    let p1jobs = [];

    let e1 = "";
    e1 += "Implement Continuity Forge Phase 1 trust-boundary work in this repo. ";
    e1 += "Read packages/operator MutationEnvelope and ProjectStore, apps/api, apps/mcp. ";
    e1 += "Tasks: (1) Ensure MutationEnvelope is the universal write contract documented and used on every mutating API/MCP path. ";
    e1 += "(2) Add or strengthen tests for expected-state conflicts and write-lease exclusivity (two holders). ";
    e1 += "(3) Add architecture or import-boundary tests: providers must not import persistence repositories; keep failure messages clear. ";
    e1 += "Do NOT add new model providers. Run pytest for touched tests. Commit-ready diffs only; no force-push. ";
    e1 += "Capability: you may edit code and run tests. ";
    e1 += "Return a short markdown receipt of files changed and commands run.";
    p1jobs.push(#{ prompt: e1, label: "p1-envelope-lease", capability_mode: "all" });

    let e2 = "";
    e2 += "Implement Continuity Forge Phase 1 security/tenancy checks. ";
    e2 += "Read apps/api auth_deps.py, bootstrap-dev route, tenant_document_key. ";
    e2 += "Tasks: (1) Tests that tenant A cannot read/write tenant B document keys. ";
    e2 += "(2) Document or gate CF_BOOTSTRAP_DEV_TENANT so bootstrap-dev cannot be used in production configs (env check + test or clear deploy README warning + code guard if missing). ";
    e2 += "Run relevant pytest. Return markdown receipt.";
    p1jobs.push(#{ prompt: e2, label: "p1-tenant-bootstrap", capability_mode: "all" });

    let e3 = "";
    e3 += "Document Phase 1 acceptance in docs/campaigns/CONTINUITY_FORGE_AUTHORITY_HARDENING_001.md ";
    e3 += "with exit gates for envelope, lease concurrency, tenant isolation, bootstrap safety. ";
    e3 += "Align with AGENTS.md mutation contract. Do not weaken PROPOSED/canon rules. Return path written.";
    p1jobs.push(#{ prompt: e3, label: "p1-campaign-doc", capability_mode: "all" });

    let p1res = parallel(p1jobs);
    let p1md = "## Phase 1 execution\n\n";
    for r in p1res {
        if r != () && r.success {
            p1md += r.output.to_string();
            p1md += "\n\n";
        } else {
            p1md += "_Agent failed_\n\n";
        }
    }
    executed.push("1");

    let v1 = "";
    v1 += "Verify Phase 1 trust-boundary work. Run: python -m pytest tests/unit/test_operator.py tests/unit/test_auth.py tests/contract/test_api.py tests/contract/test_auth_api.py -q ; ";
    v1 += "and python -m ruff check packages/operator apps/api. ";
    v1 += "Read git status / diff. Report PASS/FAIL with evidence. Fail closed if tests fail.";
    let v1r = agent(v1, #{ label: "verify-p1", capability_mode: "execute" });
    if v1r != () && v1r.success {
        verify_notes.push(v1r.output.to_string());
    } else {
        verify_notes.push("Phase 1 verify agent failed");
    }

    if phase_sel == "all" {
        await_user("user", "Phase 1 complete. Resume to continue Phase 2 (production CI), or stop.");
    }
}

// --- Phase 2 ---
if phase_sel == "2" || phase_sel == "all" {
    log("Phase 2: production-shaped validation");
    let p2jobs = [];

    let c1 = "";
    c1 += "Implement Continuity Forge Phase 2 CI packaging gate. ";
    c1 += "Edit .github/workflows/ci.yml and/or add ci-packaging.yml: build wheel+sdist with python -m build, install wheel in clean venv, run continuity-forge --help and import smoke. ";
    c1 += "Keep fast gate (validate_m0) as default PR check. Document in deploy/README or docs/SETUP.md. Return receipt.";
    p2jobs.push(#{ prompt: c1, label: "p2-packaging-ci", capability_mode: "all" });

    let c2 = "";
    c2 += "Implement Continuity Forge Phase 2 coverage floors for critical modules without arbitrary global %. ";
    c2 += "Update scripts/validate_m0.py or add scripts/validate_repo.py that enforces per-path --cov-fail-under for ";
    c2 += "packages/auth, packages/operator (mutation/lease), packages/harness pipeline store, packages/repair. ";
    c2 += "Start with achievable thresholds based on current coverage (run pytest --cov first). Wire into Makefile. Return receipt.";
    p2jobs.push(#{ prompt: c2, label: "p2-coverage", capability_mode: "all" });

    let c3 = "";
    c3 += "Implement Continuity Forge Phase 2 integration CI skeleton: GitHub Actions job with services postgres:16 and minio/minio (or bitnami), ";
    c3 += "install .[production] or needed extras, set CF_DATABASE_URL and CF_S3_*, run a minimal integration test file that skips if services missing. ";
    c3 += "Add tests/integration/test_postgres_minio_smoke.py that is skip-friendly locally. Document. Return receipt.";
    p2jobs.push(#{ prompt: c3, label: "p2-integration", capability_mode: "all" });

    let p2res = parallel(p2jobs);
    let p2md = "## Phase 2 execution\n\n";
    for r in p2res {
        if r != () && r.success {
            p2md += r.output.to_string();
            p2md += "\n\n";
        } else {
            p2md += "_Agent failed_\n\n";
        }
    }
    executed.push("2");

    let v2 = "";
    v2 += "Verify Phase 2 CI/coverage changes. Run make validate or the updated gate if renamed. ";
    v2 += "Confirm workflow YAML is valid enough (read it). Report PASS/FAIL.";
    let v2r = agent(v2, #{ label: "verify-p2", capability_mode: "execute" });
    if v2r != () && v2r.success {
        verify_notes.push(v2r.output.to_string());
    } else {
        verify_notes.push("Phase 2 verify agent failed");
    }

    if phase_sel == "all" {
        await_user("user", "Phase 2 complete. Resume for Phase 3 operator UX, or stop.");
    }
}

// --- Phase 3 ---
if phase_sel == "3" || phase_sel == "all" {
    log("Phase 3: operator review UX");
    let p3jobs = [];

    let u1 = "";
    u1 += "Improve Continuity Forge operator UI (apps/web) Phase 3 without React migration. ";
    u1 += "Separate execution success from production readiness: show claim controlled_proof_not_production_ready prominently after proof; ";
    u1 += "add validator/repair rationale summary on shot rows when receipt has repair_actions; ";
    u1 += "surface approval queue empty-state with clear next action. Keep Hallmark Terminal tokens. ";
    u1 += "Update contract test strings if needed. Return receipt.";
    p3jobs.push(#{ prompt: u1, label: "p3-ui-readiness", capability_mode: "all" });

    let u2 = "";
    u2 += "Update docs: README milestone language must distinguish implemented vs integration-tested vs production-validated. ";
    u2 += "Fix Private research vs public repo contradiction. Keep version in sync with pyproject 1.3.0 or note bump. ";
    u2 += "Return receipt.";
    p3jobs.push(#{ prompt: u2, label: "p3-docs-honesty", capability_mode: "all" });

    let p3res = parallel(p3jobs);
    for r in p3res {
        if r != () && r.success {
            verify_notes.push(r.output.to_string());
        }
    }
    executed.push("3");

    let v3 = "";
    v3 += "Verify Phase 3: run pytest tests/contract/test_api.py -q and confirm apps/web still serves key strings Run proof / Download receipt. Report PASS/FAIL.";
    let v3r = agent(v3, #{ label: "verify-p3", capability_mode: "execute" });
    if v3r != () && v3r.success {
        verify_notes.push(v3r.output.to_string());
    } else {
        verify_notes.push("Phase 3 verify agent failed");
    }

    if phase_sel == "all" {
        await_user("user", "Phase 3 complete. Resume for Phase 4 long-form scaffolding (docs-only recommended), or stop.");
    }
}

// --- Phase 4 ---
if phase_sel == "4" || phase_sel == "all" {
    log("Phase 4: long-form scalability (campaign design, minimal code)");
    let p4 = "";
    p4 += "Write docs/campaigns/CONTINUITY_FORGE_LONG_FORM_UX_001.md covering scene/shot navigation, virtualized tables, ";
    p4 += "dependency-graph invalidation, incremental compile, budget/provider telemetry, streaming workflow state. ";
    p4 += "Each item: problem, non-goal, acceptance criteria, dependency on phases 1-3. Do not implement full features unless trivial stubs. Return path.";
    let p4r = agent(p4, #{ label: "p4-long-form-campaign", capability_mode: "all" });
    executed.push("4");
    if p4r != () && p4r.success {
        verify_notes.push(p4r.output.to_string());
    } else {
        verify_notes.push("Phase 4 agent failed");
    }
}

// ========== REPORT ==========
phase("Report");

let report = "";
report += "# Continuity Forge audit-hardening — EXECUTE receipt\n\n";
report += "Mode: execute\n";
report += "Phases selected: " + phase_sel + "\n";
report += "Phases touched: ";
let first = true;
for x in executed {
    if !first { report += ", "; }
    report += x;
    first = false;
}
report += "\n\n";
report += "Campaign plan (from baseline): " + plan_path + "\n\n";
report += "## Verification notes\n\n";
for n in verify_notes {
    report += n;
    report += "\n\n---\n\n";
}
report += "## Campaign plan (reference)\n\n";
report += campaign_md;

let rpath = write_scratch_file("cf-audit-report.md", report);
complete(#{
    summary: "Execute complete for phase " + phase_sel,
    mode: "execute",
    phase: phase_sel,
    plan_path: plan_path,
    report_path: rpath,
});
