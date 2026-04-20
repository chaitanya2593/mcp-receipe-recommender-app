.PHONY: test test-verbose coverage coverage-html clean

PYTHON ?= uv run python
PYTEST ?= uv run pytest

test:
	$(PYTEST) tests/

test-verbose:
	$(PYTEST) -vv tests/

coverage:
	$(PYTEST) --cov=app --cov-report=term-missing tests/

coverage-html:
	$(PYTEST) --cov=app --cov-report=html:htmlcov --cov-report=term tests/

clean:
	rm -rf .pytest_cache .coverage htmlcov coverage.xml junit.xml test-reports reports
	find . -type d -name __pycache__ -exec rm -rf {} +
