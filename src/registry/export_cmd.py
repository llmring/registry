#!/usr/bin/env python3
"""Export registry data in different formats."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

import click


def _load_provider(models_dir: Path, provider: str) -> Dict[str, Any]:
    file = models_dir / f"{provider}.json"
    if not file.exists():
        return {}
    with open(file) as f:
        return json.load(f)


@click.command(name="export")
@click.option("--models-dir", default="models", type=click.Path(exists=True))
@click.option("--output", type=click.Choice(["markdown", "json", "csv"]), required=True)
@click.option("--include-new-fields", is_flag=True, default=True)
def export_cmd(models_dir: str, output: str, include_new_fields: bool):
    """Export registry data in various formats."""
    models_path = Path(models_dir)
    providers = ["openai", "anthropic", "google"]

    data: Dict[str, List[Dict[str, Any]]] = {}
    for prov in providers:
        content = _load_provider(models_path, prov)
        models = content.get("models", {})
        if isinstance(models, dict):
            data[prov] = list(models.values())
        else:
            data[prov] = models

    if output == "json":
        click.echo(json.dumps(data, indent=2))
        return

    if output == "markdown":
        lines: List[str] = ["# LLMRing Registry Models\n"]
        for prov, models in data.items():
            lines.append(f"## {prov.capitalize()} ({len(models)} models)")
            for m in models:
                name = m.get("model_name") or m.get("model_id")
                inp = m.get("dollars_per_million_tokens_input")
                outp = m.get("dollars_per_million_tokens_output")
                desc = m.get("description", "")
                lines.append(f"- {name}: ${inp}/$M in, ${outp}/$M out — {desc}")
        click.echo("\n".join(lines))
        return

    if output == "csv":
        # Write to stdout as CSV
        fieldnames = [
            "provider",
            "model_name",
            "display_name",
            "dollars_per_million_tokens_input",
            "dollars_per_million_tokens_output",
            "max_input_tokens",
            "max_output_tokens",
        ]
        writer = csv.DictWriter(click.get_text_stream("stdout"), fieldnames=fieldnames)
        writer.writeheader()
        for prov, models in data.items():
            for m in models:
                row = {k: m.get(k) for k in fieldnames}
                row["provider"] = prov
                writer.writerow(row)


