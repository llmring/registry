#!/usr/bin/env python3
"""Normalize draft files to follow consistent schema rules."""

import json
from pathlib import Path
from typing import Optional

import click

from .schema_utils import normalize_draft_file, generate_schema_report


@click.command(name="normalize")
@click.option("--provider", help="Provider to normalize (if not specified, uses --draft)")
@click.option("--draft", type=click.Path(exists=True), help="Specific draft file to normalize")
@click.option("--drafts-dir", default="drafts", type=click.Path(), help="Directory containing drafts")
@click.option("--dry-run", is_flag=True, help="Show what would be changed without modifying files")
@click.option("--report", is_flag=True, help="Generate schema compliance report only")
def normalize_command(
    provider: Optional[str],
    draft: Optional[str],
    drafts_dir: str,
    dry_run: bool,
    report: bool
):
    """Normalize draft files to follow consistent schema rules.

    This command standardizes:
    - Null vs empty array handling (arrays should be [], not null)
    - Metadata format (consistent 'sources' structure)
    - Boolean/numeric defaults
    - Required field validation

    Examples:
        # Normalize latest draft for a provider
        uv run llmring-registry normalize --provider openai

        # Normalize specific draft file
        uv run llmring-registry normalize --draft drafts/openai.2025-09-21.draft.json

        # Check compliance without modifying
        uv run llmring-registry normalize --provider openai --dry-run

        # Generate compliance report
        uv run llmring-registry normalize --provider openai --report
    """
    drafts_path = Path(drafts_dir)

    # Determine draft file
    if draft:
        draft_path = Path(draft)
    elif provider:
        # Find latest draft for provider
        draft_files = sorted(
            drafts_path.glob(f"{provider}.*.draft.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        if not draft_files:
            raise click.ClickException(f"No draft found for provider '{provider}' in {drafts_dir}")
        draft_path = draft_files[0]
        click.echo(f"📄 Using draft: {draft_path.name}")
    else:
        raise click.ClickException("Must specify either --provider or --draft")

    # Load draft
    with open(draft_path) as f:
        draft_data = json.load(f)

    provider_name = draft_data.get("provider", "unknown")
    model_count = len(draft_data.get("models", {}))

    # Generate report if requested
    if report:
        click.echo(f"\n📊 Schema Compliance Report for {provider_name}")
        click.echo(f"   Draft: {draft_path.name}")
        click.echo(f"   Models: {model_count}\n")

        compliance_report = generate_schema_report(draft_data)

        click.echo(f"  Total models: {compliance_report['total_models']}")
        click.echo(f"  Models with issues: {compliance_report['models_with_issues']}")
        click.echo(f"  Compliance rate: {compliance_report['compliance_rate']:.1%}")

        if compliance_report['issues']:
            click.echo(f"\n  Issues found:")
            for item in compliance_report['issues'][:10]:  # Show first 10
                click.echo(f"\n    {item['model']}:")
                for issue in item['issues']:
                    click.echo(f"      - {issue}")

            if len(compliance_report['issues']) > 10:
                click.echo(f"\n    ... and {len(compliance_report['issues']) - 10} more models with issues")

        return

    # Normalize
    click.echo(f"\n🔧 Normalizing {provider_name} draft...")
    click.echo(f"   Models: {model_count}")

    normalized = normalize_draft_file(draft_data)

    # Show what changed
    changes = []

    # Check metadata changes
    if draft_data.get("sources") != normalized.get("sources"):
        changes.append("Standardized extraction metadata")

    # Check model changes
    original_models = draft_data.get("models", {})
    normalized_models = normalized.get("models", {})

    models_changed = 0
    for model_key in original_models:
        if original_models[model_key] != normalized_models.get(model_key):
            models_changed += 1

    if models_changed > 0:
        changes.append(f"Normalized {models_changed} model records")

    if not changes:
        click.echo("  ✅ No changes needed - already compliant!")
        return

    click.echo(f"\n  Changes to be applied:")
    for change in changes:
        click.echo(f"    - {change}")

    if dry_run:
        click.echo(f"\n  🔍 Dry run - no files modified")
        click.echo(f"  Run without --dry-run to apply changes")
        return

    # Write normalized draft
    backup_path = draft_path.with_suffix('.json.backup')
    draft_path.rename(backup_path)
    click.echo(f"\n  💾 Backup saved: {backup_path.name}")

    with open(draft_path, 'w') as f:
        json.dump(normalized, f, indent=2)

    click.echo(f"  ✅ Normalized draft written: {draft_path.name}")

    # Run compliance check on normalized version
    compliance_report = generate_schema_report(normalized)
    click.echo(f"\n  📊 Post-normalization compliance: {compliance_report['compliance_rate']:.1%}")

    if compliance_report['models_with_issues'] > 0:
        click.echo(f"  ⚠️  {compliance_report['models_with_issues']} models still have issues")
        click.echo(f"     Run with --report to see details")


if __name__ == "__main__":
    normalize_command()