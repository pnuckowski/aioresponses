.PHONY: clean clean-test clean-pyc clean-build help install lint test coverage dist release
.DEFAULT_GOAL := help

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

install: ## install the package and dev dependencies
	uv sync --group dev

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .pytest_cache/
	rm -f .coverage
	rm -fr htmlcov/

lint: ## check style with flake8
	uv run flake8 aioresponses tests

test: ## run tests
	uv run pytest

coverage: ## run tests with coverage report
	uv run pytest --cov=aioresponses --cov-report=term-missing --cov-report=html

dist: clean ## build source and wheel package
	uv build
	ls -l dist

release: dist ## upload a release to PyPI
	uv publish