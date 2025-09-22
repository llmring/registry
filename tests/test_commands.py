from click.testing import CliRunner
from pathlib import Path
from registry.__main__ import cli


def test_extract_smoke(tmp_path: Path):
	r = CliRunner()
	with r.isolated_filesystem():
		# Create sources directory structure
		Path('sources/openai').mkdir(parents=True, exist_ok=True)
		# The extract command should not crash even with empty sources
		res = r.invoke(cli, ['extract', '--provider', 'openai', '--timeout', '1'])
		# Should not crash; may produce no output
		assert res.exit_code == 0


def test_promote_defaults(tmp_path: Path):
	r = CliRunner()
	with r.isolated_filesystem():
		# Prepare a minimal draft in default location
		drafts = Path('drafts'); drafts.mkdir()
		models = {
			"provider": "openai",
			"models": {
				"openai:gpt-4o": {"provider": "openai", "model_name": "gpt-4o"}
			}
		}
		(drafts / 'openai.2025-01-01.draft.json').write_text(__import__('json').dumps(models))
		# promote should find and promote the draft
		res = r.invoke(cli, ['promote', '--provider', 'openai'])
		assert res.exit_code == 0