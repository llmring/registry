from click.testing import CliRunner
from pathlib import Path
from registry.__main__ import cli


def test_extract_smoke(tmp_path: Path):
	r = CliRunner()
	with r.isolated_filesystem():
		# Create empty dirs to ensure auto-create works too
		Path('html_cache').mkdir(exist_ok=True)
		Path('pdfs').mkdir(exist_ok=True)
		res = r.invoke(cli, ['extract', '--provider', 'openai', '--timeout', '1'])
		# Should not crash; may produce an empty draft
		assert res.exit_code == 0


def test_review_and_promote_defaults(tmp_path: Path):
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
		# review should auto-find
		res = r.invoke(cli, ['review-draft', '--provider', 'openai', '--accept-all'])
		assert res.exit_code == 0
		# promote should auto-find reviewed
		res2 = r.invoke(cli, ['promote', '--provider', 'openai'])
		assert res2.exit_code == 0
