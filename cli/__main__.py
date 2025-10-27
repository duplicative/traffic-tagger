"""CLI entry point."""
import typer
from cli.main import ingest

if __name__ == "__main__":
    typer.run(ingest)
