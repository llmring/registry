import json
from registry.extraction.confidence import calculate_field_confidence, merge_with_consensus


def test_calculate_field_confidence_agreement():
	res = calculate_field_confidence(1.0, 1.0, 'dollars_per_million_tokens_input')
	assert res['confidence'] == 'certain'
	assert res['value'] == 1.0


def test_calculate_field_confidence_priority():
	# Pricing prefers HTML
	res = calculate_field_confidence(2.0, 3.0, 'dollars_per_million_tokens_input')
	assert res['value'] == 2.0
	assert res['confidence'] == 'uncertain'

	# Specs prefer PDF
	res2 = calculate_field_confidence(None, 32000, 'max_input_tokens')
	assert res2['value'] == 32000
	assert res2['confidence'] == 'probable'


def test_merge_with_consensus_basic():
	html = {
		'openai:gpt-4o': {
			'provider': 'openai', 'model_name': 'gpt-4o', 'dollars_per_million_tokens_input': 1.1
		}
	}
	pdf = {
		'openai:gpt-4o': {
			'provider': 'openai', 'model_name': 'gpt-4o', 'dollars_per_million_tokens_input': 1.2
		}
	}
	merged = merge_with_consensus(html, pdf)
	assert 'openai:gpt-4o' in merged
	# Pricing prefers HTML
	assert merged['openai:gpt-4o']['dollars_per_million_tokens_input'] == 1.1
	assert merged['openai:gpt-4o']['_confidence']['dollars_per_million_tokens_input']['confidence'] in ('uncertain', 'probable')
