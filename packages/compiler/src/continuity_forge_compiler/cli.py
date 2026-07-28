from pathlib import Path

import typer

from .compiler import compile_file

app = typer.Typer(no_args_is_help=True)


@app.command()
def compile(
    script: Path = typer.Argument(..., exists=True, dir_okay=False),
    out: Path = typer.Option(Path("out"), "--out"),
) -> None:
    document = compile_file(script)
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{script.stem}.production-ir.json"
    target.write_text(document.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(str(target))


if __name__ == "__main__":
    app()
