import subprocess
import sys


def test_cli_help_runs():
	# Ensure the console entry script runs and prints help
	completed = subprocess.run([sys.executable, '-m', 'registry.__main__', '--help'], capture_output=True, text=True)
	assert completed.returncode == 0
	assert 'Registry CLI' in completed.stdout
	# Also ensure the installed script name entry works if available
	# Not fatal if missing in dev env
	try:
		completed2 = subprocess.run(['llmring-registry', '--help'], capture_output=True, text=True)
		if completed2.returncode == 0:
			assert 'Registry CLI' in completed2.stdout
	except FileNotFoundError:
		pass
