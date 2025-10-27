#!/usr/bin/env python3
"""CLI wrapper script."""
import typer
from main import ingest

if __name__ == "__main__":
    typer.run(ingest)
