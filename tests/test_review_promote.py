from click.testing import CliRunner
from pathlib import Path
import json
import hashlib

from registry.__main__ import cli


def write_json(path: Path, data: dict):
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(json.dumps(data, indent=2))


def test_promote_workflow(tmp_path: Path):
	provider = 'openai'
	draft = {
		"provider": provider,
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
		draft_path = Path('drafts') / 'openai.2025-08-21.draft.json'
		write_json(draft_path, draft)

		# Promote the draft directly
		res = r.invoke(cli, ['promote', '--provider', provider])
		assert res.exit_code == 0

		# Verify archive and publish under pages/openai
		published = Path('pages') / provider / 'models.json'
		archived = Path('pages') / provider / 'v' / '1' / 'models.json'
		assert published.exists()
		assert archived.exists()
		published_data = json.loads(published.read_text())
		assert published_data['version'] == 1
		assert 'updated_at' in published_data
		assert 'content_sha256_jcs' in published_data
		# Recompute digest excluding the digest field itself
		tmp = dict(published_data)
		digest = tmp.pop('content_sha256_jcs')
		canonical = json.dumps(tmp, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
		assert hashlib.sha256(canonical.encode('utf-8')).hexdigest() == digest


def test_review_diff(tmp_path: Path):
	provider = 'openai'
	current = {
		"provider": provider,
		"version": 1,
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
		"models": {
			"openai:gpt-4o": {
				"provider": provider,
				"model_name": "gpt-4o",
				"display_name": "GPT-4o",
				"dollars_per_million_tokens_input": 1.10,
				"dollars_per_million_tokens_output": 4.40,
				"supports_vision": True
			},
			"openai:gpt-4o-mini": {
				"provider": provider,
				"model_name": "gpt-4o-mini",
				"display_name": "GPT-4o Mini"
			}
		}
	}

	r = CliRunner()
	with r.isolated_filesystem():
		# Setup current models
		write_json(Path('pages') / provider / 'models.json', current)
		draft_path = Path('drafts') / 'openai.2025-08-21.draft.json'
		write_json(draft_path, draft)

		# Review should produce a diff
		res = r.invoke(cli, ['review-draft', '--provider', provider])
		assert res.exit_code == 0
		diff_file = Path('drafts') / 'openai.2025-08-21.draft.diff.json'
		assert diff_file.exists()

		# Check diff content
		diff_data = json.loads(diff_file.read_text())
		assert 'openai:gpt-4o-mini' in diff_data['added']
		assert 'openai:gpt-4o' in diff_data['changed']