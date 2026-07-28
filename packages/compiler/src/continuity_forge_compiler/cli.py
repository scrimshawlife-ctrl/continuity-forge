from pathlib import Path
from typing import Annotated

import typer
from continuity_forge_ledger import build_continuity_ledger

from .compiler import compile_file

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    """Compile screenplay sources into Continuity Forge Production IR and ledgers."""


@app.command("compile")
def compile_cmd(
    script: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    out: Annotated[Path, typer.Option("--out")] = Path("out"),
    document_key: Annotated[str | None, typer.Option("--document-key")] = None,
) -> None:
    """Compile a Fountain/FDX screenplay to validated Production IR JSON."""
    document = compile_file(script, document_key=document_key)
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{script.stem}.production-ir.json"
    target.write_text(document.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(str(target))


@app.command("ledger")
def ledger_cmd(
    script: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    out: Annotated[Path, typer.Option("--out")] = Path("out"),
    document_key: Annotated[str | None, typer.Option("--document-key")] = None,
) -> None:
    """Compile a screenplay and write the derived continuity ledger JSON."""
    document = compile_file(script, document_key=document_key)
    ledger = build_continuity_ledger(document)
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{script.stem}.continuity-ledger.json"
    target.write_text(ledger.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(str(target))


if __name__ == "__main__":
    app()
