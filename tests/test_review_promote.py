from click.testing import CliRunner
from pathlib import Path
import json

from registry.__main__ import cli


def write_json(path: Path, data: dict):
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(json.dumps(data, indent=2))


def test_review_and_promote_workflow(tmp_path: Path):
	provider = 'openai'
	current = {
		"provider": provider,
		"version": 2,
		"updated_at": "2025-08-20T00:00:00Z",
		"models": {
			"openai:gpt-4o": {
				"provider": provider,
				"model_name": "gpt-4o",
				"display_name": "GPT-4o",
				"dollars_per_million_tokens_input": 1.25,
				"dollars_per_million_tokens_output": 10.0
			}
		}
	}
	draft = {
		"provider": provider,
		"version": 3,
		"updated_at": None,
		"models": {
			"openai:gpt-4o": {
				"provider": provider,
				"model_name": "gpt-4o",
				"display_name": "GPT-4o",
				"dollars_per_million_tokens_input": 1.10,
				"dollars_per_million_tokens_output": 4.40,
				"supports_vision": True
			}
		}
	}

	r = CliRunner()
	with r.isolated_filesystem():
		# Arrange inside the isolated filesystem
		write_json(Path('pages') / provider / 'models.json', current)
		draft_path = Path('drafts') / 'openai.2025-08-21.json'
		write_json(draft_path, draft)

		# Review without accept-all should produce a .diff.json
		res = r.invoke(cli, ['review-draft', '--provider', provider, '--draft', str(draft_path)])
		assert res.exit_code == 0
		assert (draft_path.with_suffix('.diff.json')).exists()

		# Accept all to generate a reviewed file
		res2 = r.invoke(cli, ['review-draft', '--provider', provider, '--draft', str(draft_path), '--accept-all'])
		assert res2.exit_code == 0
		reviewed = draft_path.with_name(f'{provider}.reviewed.json')
		assert reviewed.exists()

		# Promote reviewed
		res3 = r.invoke(cli, ['promote', '--provider', provider, '--reviewed', str(reviewed)])
		assert res3.exit_code == 0

		# Verify archive and publish under pages/openai
		published = Path('pages') / provider / 'models.json'
		archived = Path('pages') / provider / 'v' / '3' / 'models.json'
		assert published.exists()
		assert archived.exists()
		published_data = json.loads(published.read_text())
		assert published_data['version'] == 3
		assert 'updated_at' in published_data
