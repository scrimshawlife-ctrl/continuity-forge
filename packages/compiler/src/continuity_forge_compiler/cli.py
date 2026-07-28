from pathlib import Path
from typing import Annotated

import typer

from .compiler import compile_file

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    """Compile screenplay sources into Continuity Forge Production IR."""


@app.command()
def compile(
    script: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    out: Annotated[Path, typer.Option("--out")] = Path("out"),
    document_key: Annotated[str | None, typer.Option("--document-key")] = None,
) -> None:
    """Compile a Fountain screenplay to validated Production IR JSON."""
    document = compile_file(script, document_key=document_key)
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{script.stem}.production-ir.json"
    target.write_text(document.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(str(target))


if __name__ == "__main__":
    app()
