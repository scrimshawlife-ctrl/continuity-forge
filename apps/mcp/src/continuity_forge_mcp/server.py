from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from continuity_forge_compiler import compile_fdx_result, compile_text_result
from continuity_forge_ir import CompileDiagnostic, CoverageReport, NarrativeAtom, SceneNode

SourceFormat = Literal["fountain", "fdx"]


class CompileInput(BaseModel):
    title: str = "Untitled"
    text: str
    source_format: SourceFormat = "fountain"


class SceneSummary(BaseModel):
    scene_id: UUID
    ordinal: int = Field(ge=1)
    slugline: str
    atom_count: int = Field(ge=0)


class SceneInspection(BaseModel):
    scene: SceneNode
    atoms: list[NarrativeAtom]


class ReadOnlyTool(BaseModel):
    name: str
    description: str
    read_only: bool = True


class ToolRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, Callable[..., Any]] = {}
        self._metadata: dict[str, ReadOnlyTool] = {}

    def register(self, name: str, description: str, handler: Callable[..., Any]) -> None:
        if name in self._handlers:
            raise ValueError(f"Tool already registered: {name}")
        self._handlers[name] = handler
        self._metadata[name] = ReadOnlyTool(name=name, description=description)

    def list_tools(self) -> list[ReadOnlyTool]:
        return [self._metadata[name] for name in sorted(self._metadata)]

    def call(self, name: str, **arguments: Any) -> Any:
        try:
            handler = self._handlers[name]
        except KeyError as exc:
            raise KeyError(f"Unknown MCP tool: {name}") from exc
        return handler(**arguments)


def _compile(payload: CompileInput):
    if payload.source_format == "fdx":
        return compile_fdx_result(payload.text, title=payload.title)
    return compile_text_result(payload.text, title=payload.title)


def get_compile_diagnostics(
    *, title: str = "Untitled", text: str, source_format: SourceFormat = "fountain"
) -> list[CompileDiagnostic]:
    return _compile(CompileInput(title=title, text=text, source_format=source_format)).diagnostics


def audit_script_coverage(
    *, title: str = "Untitled", text: str, source_format: SourceFormat = "fountain"
) -> CoverageReport:
    return _compile(CompileInput(title=title, text=text, source_format=source_format)).coverage


def list_scenes(
    *, title: str = "Untitled", text: str, source_format: SourceFormat = "fountain"
) -> list[SceneSummary]:
    result = _compile(CompileInput(title=title, text=text, source_format=source_format))
    return [
        SceneSummary(
            scene_id=scene.scene_id,
            ordinal=scene.ordinal,
            slugline=scene.slugline,
            atom_count=len(scene.atoms),
        )
        for scene in result.document.scenes
    ]


def inspect_scene(
    *,
    scene_id: UUID | str,
    title: str = "Untitled",
    text: str,
    source_format: SourceFormat = "fountain",
) -> SceneInspection:
    requested_id = UUID(str(scene_id))
    result = _compile(CompileInput(title=title, text=text, source_format=source_format))
    for scene in result.document.scenes:
        if scene.scene_id == requested_id:
            return SceneInspection(scene=scene, atoms=scene.atoms)
    raise KeyError(f"Scene not found: {requested_id}")


def build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        "cf.get_compile_diagnostics",
        "Compile a screenplay without mutation and return typed diagnostics.",
        get_compile_diagnostics,
    )
    registry.register(
        "cf.audit_script_coverage",
        "Compile a screenplay without mutation and return source-coverage metrics.",
        audit_script_coverage,
    )
    registry.register(
        "cf.list_scenes",
        "Compile a screenplay without mutation and list deterministic scene summaries.",
        list_scenes,
    )
    registry.register(
        "cf.inspect_scene",
        "Compile a screenplay without mutation and inspect one scene by stable ID.",
        inspect_scene,
    )
    return registry


registry = build_registry()
