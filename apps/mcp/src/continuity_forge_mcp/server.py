from __future__ import annotations

from typing import Any
from uuid import UUID

from continuity_forge_compiler import compile_text
from continuity_forge_ir import ScriptDocument
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Continuity Forge")


def _compile(source: str, title: str, document_key: str | None) -> ScriptDocument:
    return compile_text(source, title=title, document_key=document_key)


@mcp.tool()
def compile_script(
    source: str,
    title: str = "Untitled",
    document_key: str | None = None,
) -> dict[str, Any]:
    """Compile Fountain source without mutating canonical state."""
    return _compile(source, title, document_key).model_dump(mode="json")


@mcp.tool()
def get_compile_diagnostics(
    source: str,
    title: str = "Untitled",
    document_key: str | None = None,
) -> list[dict[str, Any]]:
    """Return deterministic diagnostics for Fountain source."""
    document = _compile(source, title, document_key)
    return [item.model_dump(mode="json") for item in document.diagnostics]


@mcp.tool()
def list_scenes(
    source: str,
    title: str = "Untitled",
    document_key: str | None = None,
) -> list[dict[str, Any]]:
    """List compiled scenes and their stable identifiers."""
    document = _compile(source, title, document_key)
    return [
        {
            "scene_id": str(scene.scene_id),
            "ordinal": scene.ordinal,
            "slugline": scene.slugline,
            "atom_count": len(scene.atoms),
        }
        for scene in document.scenes
    ]


@mcp.tool()
def get_scene(
    source: str,
    scene_id: str,
    title: str = "Untitled",
    document_key: str | None = None,
) -> dict[str, Any] | None:
    """Get one compiled scene by stable identifier."""
    requested = UUID(scene_id)
    document = _compile(source, title, document_key)
    return next(
        (scene.model_dump(mode="json") for scene in document.scenes if scene.scene_id == requested),
        None,
    )


@mcp.tool()
def audit_script_coverage(
    source: str,
    title: str = "Untitled",
    document_key: str | None = None,
) -> dict[str, Any]:
    """Return source-accounting totals and uncovered spans."""
    return _compile(source, title, document_key).coverage.model_dump(mode="json")


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
