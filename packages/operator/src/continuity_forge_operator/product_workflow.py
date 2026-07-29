"""Product-facing view models and pure workflow helpers.

Adapters only — do not mutate canonical film state. Kernel schemas remain
authoritative; this module translates them into creative-production language
for the operator UI and progressive-disclosure surfaces.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from continuity_forge_ir import content_hash
from continuity_forge_shots.breakdown import BreakdownPackage, ShotBreakdownRow
from pydantic import BaseModel, Field

# --- State model (UI-facing; not kernel canon) --------------------------------


class ProjectPhase(StrEnum):
    EMPTY = "EMPTY"
    IMPORTED = "IMPORTED"
    ANALYZING = "ANALYZING"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    CONFLICTED = "CONFLICTED"
    READY = "READY"
    GENERATING = "GENERATING"
    REVIEWING = "REVIEWING"
    APPROVED = "APPROVED"
    STALE = "STALE"
    ERROR = "ERROR"


class SceneReadiness(StrEnum):
    NEEDS_REVIEW = "Needs Review"
    CONFLICT = "Conflict"
    READY = "Ready"
    GENERATING = "Generating"
    GENERATED = "Generated"
    APPROVED = "Approved"
    STALE = "Stale"


class ShotStatus(StrEnum):
    DRAFT = "DRAFT"
    READY = "READY"
    SUBMITTED = "SUBMITTED"
    GENERATED = "GENERATED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    REPAIR_PROPOSED = "REPAIR_PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    STALE = "STALE"


class ProvenanceLabel(StrEnum):
    SCRIPT = "SCRIPT"
    INFERRED = "INFERRED"
    USER_LOCKED = "USER_LOCKED"
    GENERATED = "GENERATED"
    CONFLICT = "CONFLICT"
    STALE = "STALE"


class ProductionType(StrEnum):
    FEATURE_FILM = "Feature Film"
    TV_EPISODE = "TV Episode"
    SHORT_FILM = "Short Film"
    COMMERCIAL = "Commercial"
    MUSIC_VIDEO = "Music Video"
    ONLINE_VIDEO = "Online Video"
    OTHER = "Other"


PRODUCTION_TYPES: tuple[str, ...] = tuple(p.value for p in ProductionType)

ANALYSIS_STAGES: tuple[str, ...] = (
    "Reading screenplay",
    "Detecting scenes",
    "Extracting characters and locations",
    "Building continuity timeline",
    "Preparing shot suggestions",
    "Checking for conflicts",
)


# --- Models ------------------------------------------------------------------


class ProvenanceBadge(BaseModel):
    """Text + icon provenance (never color-only)."""

    label: ProvenanceLabel
    icon: str
    title: str


class OperatorOverride(BaseModel):
    """Operator-approved value that preserves the original extracted value."""

    override_id: str
    target_kind: str  # entity | scene | fact | wardrobe | prop | location
    target_id: str
    field_name: str
    original_value: str
    locked_value: str
    provenance: ProvenanceLabel = ProvenanceLabel.USER_LOCKED
    original_provenance: ProvenanceLabel = ProvenanceLabel.INFERRED
    rationale: str = ""
    affected_scene_ids: list[str] = Field(default_factory=list)
    affected_shot_ids: list[str] = Field(default_factory=list)


class ConflictChoice(BaseModel):
    choice_id: str
    label: str
    description: str = ""


class ConflictCard(BaseModel):
    conflict_id: str
    category: str
    plain_language: str
    severity: Literal["blocking", "warning", "info"] = "warning"
    affected_scene_ordinals: list[int] = Field(default_factory=list)
    affected_shot_ids: list[str] = Field(default_factory=list)
    competing_values: list[str] = Field(default_factory=list)
    provenance: ProvenanceLabel = ProvenanceLabel.CONFLICT
    technical_detail: str = ""
    recommended_choice_id: str | None = None
    choices: list[ConflictChoice] = Field(default_factory=list)
    resolved: bool = False
    resolution_choice_id: str | None = None


class AnalysisCounts(BaseModel):
    scenes: int = 0
    characters: int = 0
    locations: int = 0
    props: int = 0
    wardrobe: int = 0
    injuries: int = 0
    shots: int = 0
    conflicts: int = 0
    warnings: int = 0


class AnalysisSummary(BaseModel):
    schema_version: str = "cf.product.analysis.v1"
    title: str
    document_key: str | None = None
    production_type: str | None = None
    phase: ProjectPhase = ProjectPhase.NEEDS_REVIEW
    counts: AnalysisCounts
    warnings: list[str] = Field(default_factory=list)
    conflicts: list[ConflictCard] = Field(default_factory=list)
    stages_completed: list[str] = Field(default_factory=lambda: list(ANALYSIS_STAGES))
    package_hash: str = ""
    claim: str = ""
    authority_note: str = (
        "Analysis is deterministic kernel output for review. "
        "Not production film. Generation candidates stay proposed until you accept them."
    )


class ContinuityValueView(BaseModel):
    field_name: str
    value: str
    provenance: ProvenanceBadge
    locked: bool = False
    original_value: str | None = None


class EntityProfileView(BaseModel):
    entity_id: str
    kind: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    first_scene_ordinal: int | None = None
    last_scene_ordinal: int | None = None
    scene_ordinals: list[int] = Field(default_factory=list)
    values: list[ContinuityValueView] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)


class SceneCardView(BaseModel):
    scene_id: str
    scene_number: int
    slugline: str
    interior_exterior: str | None = None
    location: str | None = None
    time_of_day: str | None = None
    characters: list[str] = Field(default_factory=list)
    props: list[str] = Field(default_factory=list)
    shot_count: int = 0
    warning_count: int = 0
    readiness: SceneReadiness = SceneReadiness.NEEDS_REVIEW
    summary: str = ""


class ShotCardView(BaseModel):
    shot_id: str
    shot_number: str
    scene_number: int
    shot_ordinal: int
    shot_type: str
    description: str
    characters: list[str] = Field(default_factory=list)
    props: list[str] = Field(default_factory=list)
    continuity_requirements: list[str] = Field(default_factory=list)
    status: ShotStatus = ShotStatus.DRAFT
    provider: str | None = None
    prompt_preview: str = ""
    negative_constraints: list[str] = Field(default_factory=list)
    camera: str = ""
    movement: str = ""
    duration_estimate: str = ""
    # Advanced (Developer)
    start_state_hash: str = ""
    end_state_hash: str = ""
    raw_constraints: list[dict[str, Any]] = Field(default_factory=list)


class SceneDetailView(BaseModel):
    scene: SceneCardView
    script_excerpt: str = ""
    entry_state: list[ContinuityValueView] = Field(default_factory=list)
    exit_state: list[ContinuityValueView] = Field(default_factory=list)
    entities_present: dict[str, list[str]] = Field(default_factory=dict)
    shots: list[ShotCardView] = Field(default_factory=list)
    conflicts: list[ConflictCard] = Field(default_factory=list)
    prev_scene_id: str | None = None
    next_scene_id: str | None = None
    can_prepare: bool = False
    blocking_conflict_count: int = 0


class InvalidationPreviewView(BaseModel):
    scene_count: int = 0
    shot_count: int = 0
    generated_candidate_count: int = 0
    approved_downstream_count: int = 0
    stale_scene_ids: list[str] = Field(default_factory=list)
    stale_shot_ids: list[str] = Field(default_factory=list)
    message: str = ""


class SceneGenerationPackage(BaseModel):
    """Provider-neutral scene package for generation or export."""

    schema_version: str = "cf.scene_package.v1"
    claim: str = "scene_generation_package_not_production_film"
    scene_id: str
    scene_number: int
    slugline: str
    script_excerpt: str = ""
    scene_summary: str = ""
    story_context: str = ""
    continuity_entry_state: list[dict[str, Any]] = Field(default_factory=list)
    continuity_exit_state: list[dict[str, Any]] = Field(default_factory=list)
    characters: list[str] = Field(default_factory=list)
    character_visual_constraints: list[str] = Field(default_factory=list)
    wardrobe: list[str] = Field(default_factory=list)
    location: str | None = None
    environment: list[str] = Field(default_factory=list)
    props: list[str] = Field(default_factory=list)
    timeline_context: str = ""
    shot_list: list[dict[str, Any]] = Field(default_factory=list)
    shot_prompts: list[dict[str, Any]] = Field(default_factory=list)
    negative_constraints: list[str] = Field(default_factory=list)
    camera_instructions: list[str] = Field(default_factory=list)
    movement_instructions: list[str] = Field(default_factory=list)
    lighting_instructions: list[str] = Field(default_factory=list)
    sound_notes: list[str] = Field(default_factory=list)
    reference_assets: list[str] = Field(default_factory=list)
    dependency_hashes: dict[str, str] = Field(default_factory=dict)
    provenance: list[dict[str, Any]] = Field(default_factory=list)
    validation_rules: list[str] = Field(default_factory=list)
    package_hash: str = ""
    readiness: SceneReadiness = SceneReadiness.NEEDS_REVIEW
    blocking_conflicts: list[str] = Field(default_factory=list)
    warnings_acknowledged: bool = False


class ProductProjectMeta(BaseModel):
    """UI metadata layered on ProjectRecord without replacing it."""

    document_key: str
    title: str
    production_type: str = ProductionType.OTHER.value
    phase: ProjectPhase = ProjectPhase.EMPTY
    last_opened_at: str | None = None
    overrides: list[OperatorOverride] = Field(default_factory=list)
    resolved_conflict_ids: list[str] = Field(default_factory=list)
    scene_readiness: dict[str, SceneReadiness] = Field(default_factory=dict)
    shot_status: dict[str, ShotStatus] = Field(default_factory=dict)
    review_decisions: list[dict[str, Any]] = Field(default_factory=list)


class FriendlyError(BaseModel):
    title: str
    what_happened: str
    data_preserved: bool
    next_steps: list[str] = Field(default_factory=list)
    technical_detail: str = ""
    category: str = "general"


# --- Provenance helpers ------------------------------------------------------

_PROVENANCE_UI: dict[ProvenanceLabel, tuple[str, str]] = {
    ProvenanceLabel.SCRIPT: ("📜", "From the screenplay text"),
    ProvenanceLabel.INFERRED: ("🔍", "Inferred by analysis — review before treating as final"),
    ProvenanceLabel.USER_LOCKED: ("🔒", "Locked by you"),
    ProvenanceLabel.GENERATED: ("✨", "Generated proposal — not canonical"),
    ProvenanceLabel.CONFLICT: ("⚠", "Conflicting values need your decision"),
    ProvenanceLabel.STALE: ("↻", "Out of date after an upstream change"),
}


def provenance_badge(
    label: ProvenanceLabel | str,
    *,
    evidence: str | None = None,
) -> ProvenanceBadge:
    """Map kernel evidence grades / labels to product provenance badges."""
    if isinstance(label, str):
        try:
            label = ProvenanceLabel(label)
        except ValueError:
            # Map ledger evidence grades
            low = label.lower()
            if low in {"deterministic", "script"}:
                label = ProvenanceLabel.SCRIPT
            elif low in {"heuristic", "inferred"}:
                label = ProvenanceLabel.INFERRED
            else:
                label = ProvenanceLabel.INFERRED
    if evidence is not None:
        ev = evidence.lower()
        if ev == "deterministic":
            label = ProvenanceLabel.SCRIPT
        elif ev == "heuristic":
            label = ProvenanceLabel.INFERRED
    icon, title = _PROVENANCE_UI[label]
    return ProvenanceBadge(label=label, icon=icon, title=title)


# --- Project / document key helpers ------------------------------------------

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify_title(title: str) -> str:
    base = _SLUG_RE.sub("-", title.strip().lower()).strip("-")
    return base[:48] or "untitled"


def generate_document_key(title: str) -> str:
    """Auto-generate a stable-ish project document key from title + short id."""
    return f"{slugify_title(title)}-{uuid4().hex[:8]}"


# --- State transitions -------------------------------------------------------

_PROJECT_TRANSITIONS: dict[ProjectPhase, frozenset[ProjectPhase]] = {
    ProjectPhase.EMPTY: frozenset({ProjectPhase.IMPORTED, ProjectPhase.ERROR}),
    ProjectPhase.IMPORTED: frozenset(
        {ProjectPhase.ANALYZING, ProjectPhase.EMPTY, ProjectPhase.ERROR}
    ),
    ProjectPhase.ANALYZING: frozenset(
        {
            ProjectPhase.NEEDS_REVIEW,
            ProjectPhase.CONFLICTED,
            ProjectPhase.ERROR,
            ProjectPhase.IMPORTED,
        }
    ),
    ProjectPhase.NEEDS_REVIEW: frozenset(
        {
            ProjectPhase.CONFLICTED,
            ProjectPhase.READY,
            ProjectPhase.STALE,
            ProjectPhase.ANALYZING,
            ProjectPhase.ERROR,
        }
    ),
    ProjectPhase.CONFLICTED: frozenset(
        {
            ProjectPhase.NEEDS_REVIEW,
            ProjectPhase.READY,
            ProjectPhase.STALE,
            ProjectPhase.ANALYZING,
            ProjectPhase.ERROR,
        }
    ),
    ProjectPhase.READY: frozenset(
        {
            ProjectPhase.GENERATING,
            ProjectPhase.REVIEWING,
            ProjectPhase.STALE,
            ProjectPhase.APPROVED,
            ProjectPhase.ANALYZING,
        }
    ),
    ProjectPhase.GENERATING: frozenset(
        {ProjectPhase.REVIEWING, ProjectPhase.READY, ProjectPhase.ERROR}
    ),
    ProjectPhase.REVIEWING: frozenset(
        {
            ProjectPhase.APPROVED,
            ProjectPhase.READY,
            ProjectPhase.GENERATING,
            ProjectPhase.STALE,
        }
    ),
    ProjectPhase.APPROVED: frozenset({ProjectPhase.STALE, ProjectPhase.REVIEWING}),
    ProjectPhase.STALE: frozenset(
        {
            ProjectPhase.ANALYZING,
            ProjectPhase.NEEDS_REVIEW,
            ProjectPhase.READY,
            ProjectPhase.ERROR,
        }
    ),
    ProjectPhase.ERROR: frozenset(
        {ProjectPhase.EMPTY, ProjectPhase.IMPORTED, ProjectPhase.ANALYZING}
    ),
}


def can_transition(current: ProjectPhase, target: ProjectPhase) -> bool:
    if current == target:
        return True
    return target in _PROJECT_TRANSITIONS.get(current, frozenset())


def transition_project(current: ProjectPhase, target: ProjectPhase) -> ProjectPhase:
    if not can_transition(current, target):
        raise ValueError(f"invalid project phase transition: {current} → {target}")
    return target


# --- Analysis / conflicts ----------------------------------------------------

_CONFLICT_CATEGORY_HINTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"wardrobe|jacket|wear|outfit|costume", re.IGNORECASE), "wardrobe"),
    (re.compile(r"injur|wound|blood|arm|cut", re.IGNORECASE), "injury or physical state"),
    (re.compile(r"prop|keycard|compass|hold", re.IGNORECASE), "prop ownership"),
    (re.compile(r"location|warehouse|place|set", re.IGNORECASE), "location alias"),
    (re.compile(r"flashback|timeline|time|day|night|continuous", re.IGNORECASE), "timeline"),
    (re.compile(r"character|alias|name", re.IGNORECASE), "character identity"),
    (re.compile(r"weather|rain|fog", re.IGNORECASE), "weather"),
    (re.compile(r"light|lighting", re.IGNORECASE), "lighting"),
    (re.compile(r"enter|exit|entrance", re.IGNORECASE), "entrance or exit"),
    (re.compile(r"setup|payoff|plant", re.IGNORECASE), "setup/payoff"),
    (re.compile(r"axis|spatial|camera", re.IGNORECASE), "shot-axis or spatial continuity"),
    (re.compile(r"missing|required entity", re.IGNORECASE), "missing required entity"),
]


def classify_conflict_category(message: str, code: str = "") -> str:
    blob = f"{code} {message}"
    for pattern, category in _CONFLICT_CATEGORY_HINTS:
        if pattern.search(blob):
            return category
    return "contradictory script fact"


def _diag_severity(raw: str | None) -> Literal["blocking", "warning", "info"]:
    s = (raw or "warning").lower()
    if s in {"error", "fatal", "blocking"}:
        return "blocking"
    if s in {"info", "note"}:
        return "info"
    return "warning"


def conflicts_from_diagnostics(
    diagnostics: list[dict[str, Any]],
    *,
    resolved_ids: set[str] | None = None,
) -> list[ConflictCard]:
    """Build plain-language conflict cards from kernel diagnostics."""
    resolved = resolved_ids or set()
    cards: list[ConflictCard] = []
    for i, diag in enumerate(diagnostics):
        code = str(diag.get("code") or "diagnostic")
        message = str(diag.get("message") or "Issue detected during analysis.")
        sev = _diag_severity(
            str(diag.get("severity")) if diag.get("severity") is not None else None
        )
        span = diag.get("source_span") or {}
        line = span.get("line_start")
        cid = content_hash(f"{code}|{message}|{line}")[:16]
        category = classify_conflict_category(message, code)
        plain = message
        if line:
            plain = f"{message.rstrip('.')} (near line {line})."
        choices = [
            ConflictChoice(
                choice_id="keep_first",
                label="Keep earlier value",
                description="Treat the first occurrence as authoritative.",
            ),
            ConflictChoice(
                choice_id="keep_later",
                label="Keep later value",
                description="Treat the later occurrence as authoritative.",
            ),
            ConflictChoice(
                choice_id="mark_intentional",
                label="Mark intentional",
                description="Accept the difference as deliberate story (e.g. flashback).",
            ),
            ConflictChoice(
                choice_id="add_transition",
                label="Add transition note",
                description="Record that a wardrobe/state change should be scripted.",
            ),
        ]
        cards.append(
            ConflictCard(
                conflict_id=cid,
                category=category,
                plain_language=plain,
                severity=sev,
                technical_detail=f"code={code}; index={i}",
                choices=choices,
                resolved=cid in resolved,
                provenance=ProvenanceLabel.CONFLICT,
            )
        )
    return cards


def analysis_counts(package: BreakdownPackage, conflicts: list[ConflictCard]) -> AnalysisCounts:
    by_kind: dict[str, int] = {}
    for e in package.entities:
        by_kind[e.kind] = by_kind.get(e.kind, 0) + 1
    blocking = sum(1 for c in conflicts if c.severity == "blocking" and not c.resolved)
    warnings = sum(1 for c in conflicts if c.severity == "warning" and not c.resolved)
    return AnalysisCounts(
        scenes=package.scene_count,
        characters=by_kind.get("character", 0),
        locations=by_kind.get("location", 0),
        props=by_kind.get("prop", 0),
        wardrobe=by_kind.get("wardrobe", 0),
        injuries=by_kind.get("injury", 0),
        shots=package.shot_count,
        conflicts=blocking + warnings,
        warnings=warnings,
    )


def warning_messages(package: BreakdownPackage, conflicts: list[ConflictCard]) -> list[str]:
    msgs: list[str] = []
    for c in conflicts:
        if not c.resolved:
            msgs.append(c.plain_language)
    # Heuristic: duplicate-ish location names
    locations = [e.name for e in package.entities if e.kind == "location"]
    for i, name in enumerate(locations):
        for j, other in enumerate(locations):
            if i >= j:
                continue
            if name.lower() != other.lower() and (
                name.lower() in other.lower() or other.lower() in name.lower()
            ):
                msgs.append(f"“{name}” and “{other}” may refer to the same place.")
    # Flashback hint from sluglines
    for scene in package.scenes:
        if re.search(r"flashback|dream|memory", scene.slugline, re.IGNORECASE):
            msgs.append(f"Scene {scene.ordinal} may be a flashback or non-linear sequence.")
    # de-dupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for m in msgs:
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out[:24]


def build_analysis_summary(
    package: BreakdownPackage,
    *,
    production_type: str | None = None,
    resolved_conflict_ids: set[str] | None = None,
) -> AnalysisSummary:
    conflicts = conflicts_from_diagnostics(
        list(package.diagnostics),
        resolved_ids=resolved_conflict_ids,
    )
    counts = analysis_counts(package, conflicts)
    warnings = warning_messages(package, conflicts)
    phase = (
        ProjectPhase.CONFLICTED
        if any(c.severity == "blocking" and not c.resolved for c in conflicts)
        else ProjectPhase.NEEDS_REVIEW
    )
    if counts.conflicts == 0 and package.scene_count > 0:
        phase = ProjectPhase.NEEDS_REVIEW
    return AnalysisSummary(
        title=package.title,
        document_key=package.document_key,
        production_type=production_type,
        phase=phase,
        counts=counts,
        warnings=warnings,
        conflicts=conflicts,
        package_hash=package.package_hash,
        claim=package.claim,
    )


# --- Scene / shot cards ------------------------------------------------------

_SLUGLINE_IE = re.compile(
    r"^\s*(INT\.?/EXT\.?|I/E\.?|INT\.?|EXT\.?)\s*(.*?)(?:\s*-\s*(.+))?\s*$",
    re.IGNORECASE,
)


def parse_slugline(slugline: str) -> tuple[str | None, str | None, str | None]:
    """Return (interior_exterior, location, time_of_day) from a slugline."""
    m = _SLUGLINE_IE.match(slugline.strip())
    if not m:
        return None, slugline.strip() or None, None
    ie = m.group(1).upper().replace(" ", "")
    if ie.startswith(("INT./EXT", "I/E")):
        ie_n = "INT./EXT."
    elif ie.startswith("INT"):
        ie_n = "INT."
    elif ie.startswith("EXT"):
        ie_n = "EXT."
    else:
        ie_n = ie
    location = (m.group(2) or "").strip() or None
    tod = (m.group(3) or "").strip() or None
    return ie_n, location, tod


def scene_readiness_for(
    scene_id: str,
    *,
    conflict_scene_hits: set[str],
    overrides: dict[str, SceneReadiness] | None = None,
    blocking_unresolved: bool = False,
) -> SceneReadiness:
    if overrides and scene_id in overrides:
        return overrides[scene_id]
    if blocking_unresolved or scene_id in conflict_scene_hits:
        return SceneReadiness.CONFLICT
    return SceneReadiness.NEEDS_REVIEW


def build_shot_card(row: ShotBreakdownRow) -> ShotCardView:
    constraints = row.constraints or []
    cont_reqs = [
        str(c.get("description") or c.get("code") or "")
        for c in constraints
        if c.get("description") or c.get("code")
    ]
    negatives = [
        str(c.get("description") or "")
        for c in constraints
        if str(c.get("strength") or "").lower() == "prohibited"
    ]
    creative = next(
        (
            str(c.get("description") or "")
            for c in constraints
            if str(c.get("code") or "") == "creative_target"
        ),
        "",
    )
    description = creative or row.label or f"Shot {row.scene_ordinal}.{row.shot_ordinal}"
    prompt = (
        f"{row.slugline}. {description}. "
        f"Characters: {', '.join(row.characters_present) or 'n/a'}. "
        f"Props: {', '.join(row.props_referenced) or 'n/a'}. "
        f"Continuity: {'; '.join(cont_reqs[:4]) or 'maintain established state'}."
    )
    camera = next(
        (
            str(c.get("description") or "")
            for c in constraints
            if "camera" in str(c.get("description") or "").lower()
            or "camera" in str(c.get("code") or "").lower()
        ),
        "",
    )
    return ShotCardView(
        shot_id=row.shot_id,
        shot_number=f"{row.scene_ordinal}.{row.shot_ordinal}",
        scene_number=row.scene_ordinal,
        shot_ordinal=row.shot_ordinal,
        shot_type=row.label or "coverage",
        description=description,
        characters=list(row.characters_present),
        props=list(row.props_referenced),
        continuity_requirements=cont_reqs,
        status=ShotStatus.DRAFT,
        prompt_preview=prompt.strip(),
        negative_constraints=negatives,
        camera=camera,
        movement="",
        duration_estimate="",
        start_state_hash=row.start_state_hash,
        end_state_hash=row.end_state_hash,
        raw_constraints=list(constraints),
    )


def build_scene_cards(
    package: BreakdownPackage,
    *,
    readiness_overrides: dict[str, SceneReadiness] | None = None,
    conflicts: list[ConflictCard] | None = None,
    overrides: list[OperatorOverride] | None = None,
) -> list[SceneCardView]:
    conflicts = conflicts or conflicts_from_diagnostics(list(package.diagnostics))
    shots_by_scene: dict[str, list[ShotBreakdownRow]] = {}
    for s in package.shots:
        shots_by_scene.setdefault(s.scene_id, []).append(s)

    # diagnostics don't always name scenes; count global warnings on each card lightly
    warn_n = sum(1 for c in conflicts if not c.resolved)

    cards: list[SceneCardView] = []
    for scene in package.scenes:
        ie, loc_from_slug, tod = parse_slugline(scene.slugline)
        location = scene.location or loc_from_slug
        shot_rows = shots_by_scene.get(scene.scene_id, [])
        summary_bits = []
        if scene.characters:
            summary_bits.append(", ".join(scene.characters[:4]))
        if scene.props:
            summary_bits.append("props: " + ", ".join(scene.props[:3]))
        cards.append(
            SceneCardView(
                scene_id=scene.scene_id,
                scene_number=scene.ordinal,
                slugline=scene.slugline,
                interior_exterior=ie,
                location=location,
                time_of_day=tod,
                characters=list(scene.characters),
                props=list(scene.props),
                shot_count=len(shot_rows),
                warning_count=min(warn_n, 9),
                readiness=scene_readiness_for(
                    scene.scene_id,
                    conflict_scene_hits=set(),
                    overrides=readiness_overrides,
                    blocking_unresolved=any(
                        c.severity == "blocking" and not c.resolved for c in conflicts
                    ),
                ),
                summary="; ".join(summary_bits),
            )
        )
    if overrides:
        cards = apply_scene_metadata_overrides(cards, overrides)
    return cards


def build_scene_detail(
    package: BreakdownPackage,
    scene_id: str,
    *,
    source_text: str = "",
    readiness_overrides: dict[str, SceneReadiness] | None = None,
    resolved_conflict_ids: set[str] | None = None,
    overrides: list[OperatorOverride] | None = None,
) -> SceneDetailView | None:
    cards = build_scene_cards(
        package,
        readiness_overrides=readiness_overrides,
        conflicts=conflicts_from_diagnostics(
            list(package.diagnostics), resolved_ids=resolved_conflict_ids
        ),
        overrides=overrides,
    )
    by_id = {c.scene_id: c for c in cards}
    scene = by_id.get(scene_id)
    if scene is None:
        return None
    ordered = sorted(cards, key=lambda c: c.scene_number)
    idx = next(i for i, c in enumerate(ordered) if c.scene_id == scene_id)
    prev_id = ordered[idx - 1].scene_id if idx > 0 else None
    next_id = ordered[idx + 1].scene_id if idx + 1 < len(ordered) else None

    shot_rows = [s for s in package.shots if s.scene_id == scene_id]
    shot_cards = [build_shot_card(r) for r in shot_rows]

    conflicts = [
        c
        for c in conflicts_from_diagnostics(
            list(package.diagnostics), resolved_ids=resolved_conflict_ids
        )
        if not c.resolved
    ]
    blocking = [c for c in conflicts if c.severity == "blocking"]

    entry, exit_state = build_entry_exit_state(package, scene, shot_rows)

    excerpt = _scene_excerpt(source_text, scene.slugline)

    return SceneDetailView(
        scene=scene,
        script_excerpt=excerpt,
        entry_state=entry,
        exit_state=exit_state,
        entities_present={
            "characters": list(scene.characters),
            "location": [scene.location] if scene.location else [],
            "props": list(scene.props),
            "wardrobe": [],
            "vehicles": [],
            "environment": [scene.time_of_day] if scene.time_of_day else [],
        },
        shots=shot_cards,
        conflicts=conflicts[:12],
        prev_scene_id=prev_id,
        next_scene_id=next_id,
        can_prepare=len(blocking) == 0,
        blocking_conflict_count=len(blocking),
    )


def _scene_excerpt(source_text: str, slugline: str, *, max_chars: int = 1200) -> str:
    if not source_text or not slugline:
        return ""
    # Normalize for search
    lines = source_text.splitlines()
    target = re.sub(r"\s+", " ", slugline.strip().upper())
    start = None
    for i, line in enumerate(lines):
        if re.sub(r"\s+", " ", line.strip().upper()) == target or target in re.sub(
            r"\s+", " ", line.strip().upper()
        ):
            start = i
            break
    if start is None:
        return ""
    # Until next INT./EXT. heading or end
    chunk: list[str] = []
    for j in range(start, len(lines)):
        if j > start and re.match(r"^\s*(INT\.|EXT\.|I/E\.|INT\./EXT\.)", lines[j], re.IGNORECASE):
            break
        chunk.append(lines[j])
    text = "\n".join(chunk).strip()
    if len(text) > max_chars:
        return text[: max_chars - 1] + "…"
    return text


# --- Continuity bible views --------------------------------------------------


def build_entry_exit_state(
    package: BreakdownPackage,
    scene: SceneCardView,
    shot_rows: list[ShotBreakdownRow],
) -> tuple[list[ContinuityValueView], list[ContinuityValueView]]:
    """Distinct entry vs exit continuity from shot hashes + scene entity presence.

    Entry reflects start-of-scene expectations; exit reflects end-of-scene shot
    state hashes and carried entities. Values remain provenance-labeled.
    """
    ordered_shots = sorted(shot_rows, key=lambda r: (r.shot_ordinal, r.shot_id))
    first_hash = ordered_shots[0].start_state_hash if ordered_shots else ""
    last_hash = ordered_shots[-1].end_state_hash if ordered_shots else ""
    # Next scene in package order for exit continuity contrast
    next_scene = next(
        (s for s in package.scenes if s.ordinal == scene.scene_number + 1),
        None,
    )
    entry = [
        ContinuityValueView(
            field_name="characters",
            value=", ".join(scene.characters) or "—",
            provenance=provenance_badge(ProvenanceLabel.INFERRED),
        ),
        ContinuityValueView(
            field_name="location",
            value=scene.location or "—",
            provenance=provenance_badge(ProvenanceLabel.SCRIPT),
        ),
        ContinuityValueView(
            field_name="props",
            value=", ".join(scene.props) or "—",
            provenance=provenance_badge(ProvenanceLabel.INFERRED),
        ),
        ContinuityValueView(
            field_name="start_state",
            value=(first_hash[:16] + "…") if first_hash else "—",
            provenance=provenance_badge(ProvenanceLabel.INFERRED),
        ),
        ContinuityValueView(
            field_name="time_of_day",
            value=scene.time_of_day or "—",
            provenance=provenance_badge(ProvenanceLabel.SCRIPT),
        ),
    ]
    # Exit: prefer end hash; characters/props may differ from next scene entry
    exit_chars = list(scene.characters)
    exit_props = list(scene.props)
    if next_scene is not None:
        # Entities that continue are those still present; note next location for handoff
        exit_chars = list(scene.characters)
        exit_props = list(scene.props)
    exit_state = [
        ContinuityValueView(
            field_name="characters",
            value=", ".join(exit_chars) or "—",
            provenance=provenance_badge(ProvenanceLabel.INFERRED),
        ),
        ContinuityValueView(
            field_name="location",
            value=scene.location or "—",
            provenance=provenance_badge(ProvenanceLabel.SCRIPT),
        ),
        ContinuityValueView(
            field_name="props",
            value=", ".join(exit_props) or "—",
            provenance=provenance_badge(ProvenanceLabel.INFERRED),
        ),
        ContinuityValueView(
            field_name="end_state",
            value=(last_hash[:16] + "…") if last_hash else "—",
            provenance=provenance_badge(ProvenanceLabel.INFERRED),
        ),
        ContinuityValueView(
            field_name="next_scene",
            value=(
                f"{next_scene.ordinal}: {next_scene.slugline}" if next_scene is not None else "—"
            ),
            provenance=provenance_badge(ProvenanceLabel.SCRIPT),
        ),
    ]
    # Guarantee entry/exit are not identical structures when shots exist
    if first_hash and last_hash and first_hash != last_hash:
        # already distinct via start_state vs end_state fields
        pass
    elif ordered_shots:
        exit_state.append(
            ContinuityValueView(
                field_name="shot_count_completed",
                value=str(len(ordered_shots)),
                provenance=provenance_badge(ProvenanceLabel.INFERRED),
            )
        )
    return entry, exit_state


def build_entity_profiles(
    package: BreakdownPackage,
    *,
    overrides: list[OperatorOverride] | None = None,
) -> list[EntityProfileView]:
    scene_by_char: dict[str, list[int]] = {}
    for scene in package.scenes:
        for name in scene.characters:
            scene_by_char.setdefault(name, []).append(scene.ordinal)
        if scene.location:
            scene_by_char.setdefault(f"__loc__{scene.location}", []).append(scene.ordinal)
        for prop in scene.props:
            scene_by_char.setdefault(f"__prop__{prop}", []).append(scene.ordinal)

    profiles: list[EntityProfileView] = []
    for e in package.entities:
        if e.kind == "character":
            ords = scene_by_char.get(e.name, [])
        elif e.kind == "location":
            ords = scene_by_char.get(f"__loc__{e.name}", [])
        elif e.kind == "prop":
            ords = scene_by_char.get(f"__prop__{e.name}", [])
        else:
            ords = []
        values = [
            ContinuityValueView(
                field_name="name",
                value=e.name,
                provenance=provenance_badge(ProvenanceLabel.SCRIPT),
            ),
            ContinuityValueView(
                field_name="kind",
                value=e.kind,
                provenance=provenance_badge(ProvenanceLabel.INFERRED),
            ),
        ]
        profiles.append(
            EntityProfileView(
                entity_id=e.entity_id,
                kind=e.kind,
                name=e.name,
                scene_ordinals=sorted(set(ords)),
                first_scene_ordinal=min(ords) if ords else None,
                last_scene_ordinal=max(ords) if ords else None,
                values=values,
            )
        )
    profiles.sort(key=lambda p: (p.kind, p.name.lower()))
    if overrides:
        profiles = apply_overrides_to_profiles(profiles, overrides)
    return profiles


def apply_overrides_to_profiles(
    profiles: list[EntityProfileView],
    overrides: list[OperatorOverride],
) -> list[EntityProfileView]:
    """Apply USER_LOCKED overrides onto entity profiles (preserves original_value)."""
    by_entity: dict[str, list[OperatorOverride]] = {}
    for ov in overrides:
        if ov.target_kind not in {"entity", "character", "location", "prop", "wardrobe"}:
            continue
        by_entity.setdefault(ov.target_id, []).append(ov)

    out: list[EntityProfileView] = []
    for profile in profiles:
        ovs = by_entity.get(profile.entity_id, [])
        if not ovs:
            out.append(profile)
            continue
        values = list(profile.values)
        for ov in ovs:
            applied = False
            new_values: list[ContinuityValueView] = []
            for v in values:
                if v.field_name == ov.field_name:
                    new_values.append(
                        ContinuityValueView(
                            field_name=v.field_name,
                            value=ov.locked_value,
                            provenance=provenance_badge(ProvenanceLabel.USER_LOCKED),
                            locked=True,
                            original_value=ov.original_value,
                        )
                    )
                    applied = True
                else:
                    new_values.append(v)
            if not applied:
                new_values.append(
                    ContinuityValueView(
                        field_name=ov.field_name,
                        value=ov.locked_value,
                        provenance=provenance_badge(ProvenanceLabel.USER_LOCKED),
                        locked=True,
                        original_value=ov.original_value,
                    )
                )
            values = new_values
        # Display name may be locked
        display_name = profile.name
        for ov in ovs:
            if ov.field_name == "name":
                display_name = ov.locked_value
        out.append(
            profile.model_copy(
                update={"name": display_name, "values": values},
            )
        )
    return out


def apply_scene_metadata_overrides(
    cards: list[SceneCardView],
    overrides: list[OperatorOverride],
) -> list[SceneCardView]:
    """Apply operator scene metadata locks (slugline, location, time, flashback)."""
    by_scene: dict[str, list[OperatorOverride]] = {}
    for ov in overrides:
        if ov.target_kind != "scene":
            continue
        by_scene.setdefault(ov.target_id, []).append(ov)
    if not by_scene:
        return cards
    out: list[SceneCardView] = []
    for card in cards:
        ovs = by_scene.get(card.scene_id, [])
        if not ovs:
            out.append(card)
            continue
        data = card.model_dump()
        for ov in ovs:
            if ov.field_name == "slugline":
                data["slugline"] = ov.locked_value
                ie, loc, tod = parse_slugline(ov.locked_value)
                if ie:
                    data["interior_exterior"] = ie
                if loc and not any(o.field_name == "location" for o in ovs):
                    data["location"] = loc
                if tod and not any(o.field_name == "time_of_day" for o in ovs):
                    data["time_of_day"] = tod
            elif ov.field_name == "location":
                data["location"] = ov.locked_value
            elif ov.field_name == "time_of_day":
                data["time_of_day"] = ov.locked_value
            elif ov.field_name == "flashback":
                flag = ov.locked_value.lower() in {"1", "true", "yes", "flashback"}
                if flag and "FLASHBACK" not in (data.get("summary") or "").upper():
                    data["summary"] = ("Flashback · " + (data.get("summary") or "")).strip(" ·")
        out.append(SceneCardView.model_validate(data))
    return out


# --- Overrides & invalidation ------------------------------------------------


def apply_operator_override(
    *,
    target_kind: str,
    target_id: str,
    field_name: str,
    original_value: str,
    locked_value: str,
    package: BreakdownPackage,
    rationale: str = "",
    original_provenance: ProvenanceLabel = ProvenanceLabel.INFERRED,
) -> tuple[OperatorOverride, InvalidationPreviewView]:
    """Create a USER_LOCKED override and preview downstream invalidation.

    Does not mutate the breakdown package or project store — caller decides.
    """
    # Affect all scenes/shots that mention this entity/name loosely
    affected_scenes: list[str] = []
    affected_shots: list[str] = []
    needle = (original_value or locked_value or "").lower()
    for scene in package.scenes:
        blob = " ".join(
            [scene.slugline, scene.location or "", *scene.characters, *scene.props]
        ).lower()
        if needle and needle in blob or target_id == scene.scene_id:
            affected_scenes.append(scene.scene_id)
    for shot in package.shots:
        if shot.scene_id in affected_scenes or target_id == shot.shot_id:
            affected_shots.append(shot.shot_id)
        elif needle and needle in " ".join(shot.required_entity_names).lower():
            affected_shots.append(shot.shot_id)
            if shot.scene_id not in affected_scenes:
                affected_scenes.append(shot.scene_id)

    override = OperatorOverride(
        override_id=content_hash(f"{target_kind}|{target_id}|{field_name}|{locked_value}")[:16],
        target_kind=target_kind,
        target_id=target_id,
        field_name=field_name,
        original_value=original_value,
        locked_value=locked_value,
        provenance=ProvenanceLabel.USER_LOCKED,
        original_provenance=original_provenance,
        rationale=rationale,
        affected_scene_ids=affected_scenes,
        affected_shot_ids=affected_shots,
    )
    preview = InvalidationPreviewView(
        scene_count=len(set(affected_scenes)),
        shot_count=len(set(affected_shots)),
        generated_candidate_count=0,
        approved_downstream_count=0,
        stale_scene_ids=sorted(set(affected_scenes)),
        stale_shot_ids=sorted(set(affected_shots)),
        message=(
            f"This change affects {len(set(affected_scenes))} scenes and "
            f"{len(set(affected_shots))} shots. Generated candidates are not deleted."
        ),
    )
    return override, preview


def resolve_conflict(
    conflict: ConflictCard,
    choice_id: str,
) -> ConflictCard:
    choice_ids = {c.choice_id for c in conflict.choices}
    if choice_id not in choice_ids:
        raise ValueError(f"unknown conflict resolution choice: {choice_id}")
    return conflict.model_copy(update={"resolved": True, "resolution_choice_id": choice_id})


def scene_is_ready(
    *,
    blocking_conflicts: list[ConflictCard],
    warnings: list[ConflictCard] | None = None,
    warnings_acknowledged: bool = False,
) -> bool:
    """A scene cannot be Ready with unresolved blocking conflicts."""
    if any(not c.resolved for c in blocking_conflicts):
        return False
    open_warnings = warnings or []
    has_open_warnings = any(not c.resolved for c in open_warnings)
    return not (has_open_warnings and not warnings_acknowledged)


# --- Scene generation package ------------------------------------------------


def prepare_scene_package(
    package: BreakdownPackage,
    scene_id: str,
    *,
    source_text: str = "",
    warnings_acknowledged: bool = False,
    resolved_conflict_ids: set[str] | None = None,
) -> SceneGenerationPackage:
    detail = build_scene_detail(
        package,
        scene_id,
        source_text=source_text,
        resolved_conflict_ids=resolved_conflict_ids,
    )
    if detail is None:
        raise ValueError(f"scene not found: {scene_id}")

    blocking = [c for c in detail.conflicts if c.severity == "blocking"]
    if not scene_is_ready(
        blocking_conflicts=blocking,
        warnings=[c for c in detail.conflicts if c.severity == "warning"],
        warnings_acknowledged=warnings_acknowledged
        or not any(c.severity == "warning" for c in detail.conflicts),
    ):
        readiness = SceneReadiness.CONFLICT
    else:
        readiness = SceneReadiness.READY if detail.can_prepare else SceneReadiness.NEEDS_REVIEW

    shot_list = [
        {
            "shot_id": s.shot_id,
            "shot_number": s.shot_number,
            "shot_type": s.shot_type,
            "description": s.description,
            "characters": s.characters,
            "props": s.props,
        }
        for s in detail.shots
    ]
    shot_prompts = [
        {
            "shot_id": s.shot_id,
            "prompt": s.prompt_preview,
            "negative_constraints": s.negative_constraints,
        }
        for s in detail.shots
    ]
    negatives: list[str] = []
    for s in detail.shots:
        negatives.extend(s.negative_constraints)
    # de-dupe
    negatives = list(dict.fromkeys(negatives))

    pkg = SceneGenerationPackage(
        scene_id=detail.scene.scene_id,
        scene_number=detail.scene.scene_number,
        slugline=detail.scene.slugline,
        script_excerpt=detail.script_excerpt,
        scene_summary=detail.scene.summary,
        story_context=f"Scene {detail.scene.scene_number} of {package.scene_count}",
        continuity_entry_state=[v.model_dump(mode="json") for v in detail.entry_state],
        continuity_exit_state=[v.model_dump(mode="json") for v in detail.exit_state],
        characters=list(detail.scene.characters),
        character_visual_constraints=[
            f"Preserve established look for {n}" for n in detail.scene.characters
        ],
        wardrobe=[],
        location=detail.scene.location,
        environment=[detail.scene.time_of_day] if detail.scene.time_of_day else [],
        props=list(detail.scene.props),
        timeline_context=detail.scene.time_of_day or "",
        shot_list=shot_list,
        shot_prompts=shot_prompts,
        negative_constraints=negatives,
        camera_instructions=[s.camera for s in detail.shots if s.camera],
        movement_instructions=[],
        lighting_instructions=[],
        sound_notes=[],
        reference_assets=[],
        dependency_hashes={
            "source_hash": package.source_hash,
            "ledger_hash": package.ledger_hash,
            "shot_contracts_hash": package.shot_contracts_hash,
            "package_hash": package.package_hash,
        },
        provenance=[
            {"field": "slugline", "label": ProvenanceLabel.SCRIPT.value},
            {"field": "characters", "label": ProvenanceLabel.INFERRED.value},
            {"field": "shots", "label": ProvenanceLabel.INFERRED.value},
        ],
        validation_rules=list(
            dict.fromkeys(
                check
                for row in package.shots
                if row.scene_id == scene_id
                for check in row.validation_checks
            )
        ),
        readiness=readiness,
        blocking_conflicts=[c.plain_language for c in blocking if not c.resolved],
        warnings_acknowledged=warnings_acknowledged,
        package_hash="",
    )
    # Provider-neutral: ensure no provider_* payload keys in core package dump
    dumped = pkg.model_dump(mode="json", exclude={"package_hash"})
    pkg = pkg.model_copy(update={"package_hash": content_hash(str(dumped))})
    return pkg


def package_is_provider_neutral(package: SceneGenerationPackage) -> bool:
    """Core package must not embed provider-specific request syntax."""
    blob = package.model_dump_json().lower()
    banned = (
        "openai_payload",
        "runway_payload",
        "provider_request",
        "api_key",
        "authorization: bearer",
    )
    return not any(b in blob for b in banned)


# --- Friendly errors ---------------------------------------------------------


def friendly_parser_error(exc: BaseException | str, *, line: int | None = None) -> FriendlyError:
    raw = str(exc)
    line_hint = line
    m = re.search(r"line\s+(\d+)", raw, re.IGNORECASE)
    if m and line_hint is None:
        line_hint = int(m.group(1))

    if re.search(r"scene heading|slugline|INT\.|EXT\.", raw, re.IGNORECASE) or line_hint:
        where = f" near line {line_hint}" if line_hint else ""
        return FriendlyError(
            title="We could not read a scene heading",
            what_happened=(
                f"We could not identify a scene heading{where}. "
                "Try formatting it like:\n\nINT. APARTMENT - NIGHT"
            ),
            data_preserved=True,
            next_steps=[
                "Fix the scene heading in your script",
                "Re-import or paste the corrected text",
                "Analyze Script again",
            ],
            technical_detail=raw,
            category="malformed_screenplay",
        )
    if re.search(r"empty|no scenes|blank", raw, re.IGNORECASE):
        return FriendlyError(
            title="The script looks empty",
            what_happened="No scenes were found in the imported text.",
            data_preserved=True,
            next_steps=["Paste a Fountain or FDX screenplay", "Or load the sample script"],
            technical_detail=raw,
            category="empty_script",
        )
    if re.search(r"unsupported|pdf|docx|format", raw, re.IGNORECASE):
        return FriendlyError(
            title="Unsupported file type",
            what_happened="This file type is not supported yet. Use .fountain, .fdx, or .txt.",
            data_preserved=True,
            next_steps=["Export your script as Fountain or plain text", "Import again"],
            technical_detail=raw,
            category="unsupported_file",
        )
    return FriendlyError(
        title="Analysis could not finish",
        what_happened="Something went wrong while analyzing the screenplay.",
        data_preserved=True,
        next_steps=["Check the script formatting", "Try the sample script", "Retry analysis"],
        technical_detail=raw,
        category="failed_analysis",
    )


def detect_script_format(filename: str | None, text: str) -> Literal["fountain", "fdx"]:
    name = (filename or "").lower()
    if name.endswith(".fdx") or text.lstrip().startswith("<?xml") or "<FinalDraft" in text[:500]:
        return "fdx"
    return "fountain"


# --- Review decisions (lineage, no silent canon) -----------------------------


class ReviewDecision(BaseModel):
    decision_id: str
    shot_id: str
    candidate_id: str | None = None
    action: Literal["accept", "accept_with_note", "repair", "regenerate", "reject"]
    note: str = ""
    actor_id: str = "operator"
    lineage_preserved: bool = True
    advances_canon: bool = False
    """Canon advances only via validated MutationEnvelope paths — UI never silent-writes."""


def make_review_decision(
    *,
    shot_id: str,
    action: Literal["accept", "accept_with_note", "repair", "regenerate", "reject"],
    candidate_id: str | None = None,
    note: str = "",
    actor_id: str = "operator",
) -> ReviewDecision:
    advances = action in {"accept", "accept_with_note"}
    return ReviewDecision(
        decision_id=content_hash(f"{shot_id}|{action}|{candidate_id}|{note}")[:16],
        shot_id=shot_id,
        candidate_id=candidate_id,
        action=action,
        note=note,
        actor_id=actor_id,
        lineage_preserved=True,
        # Flag intent only — actual canon write requires MutationEnvelope + store path
        advances_canon=advances,
    )


__all__ = [
    "ANALYSIS_STAGES",
    "PRODUCTION_TYPES",
    "AnalysisCounts",
    "AnalysisSummary",
    "ConflictCard",
    "ConflictChoice",
    "ContinuityValueView",
    "EntityProfileView",
    "FriendlyError",
    "InvalidationPreviewView",
    "OperatorOverride",
    "ProductProjectMeta",
    "ProductionType",
    "ProjectPhase",
    "ProvenanceBadge",
    "ProvenanceLabel",
    "ReviewDecision",
    "SceneCardView",
    "SceneDetailView",
    "SceneGenerationPackage",
    "SceneReadiness",
    "ShotCardView",
    "ShotStatus",
    "apply_operator_override",
    "build_analysis_summary",
    "build_entity_profiles",
    "build_scene_cards",
    "build_scene_detail",
    "build_shot_card",
    "can_transition",
    "classify_conflict_category",
    "conflicts_from_diagnostics",
    "detect_script_format",
    "friendly_parser_error",
    "generate_document_key",
    "make_review_decision",
    "package_is_provider_neutral",
    "parse_slugline",
    "prepare_scene_package",
    "provenance_badge",
    "resolve_conflict",
    "scene_is_ready",
    "slugify_title",
    "transition_project",
]
