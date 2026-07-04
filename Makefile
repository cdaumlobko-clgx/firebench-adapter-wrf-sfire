# Declare these targets as phony to avoid conflicts with files of the same name
.PHONY: test test-cov lint update-lint-score code-formatting fix-code-formatting bandit update-docs-changelog docs clean clean-build install-build-tools build check-dist upload-test upload

PYTHON ?= python

test:
	$(PYTHON) -m pytest tests

test-cov:
	$(PYTHON) -m pytest --cov-report term-missing --cov=src/firebench_adapter_wrf_sfire tests

lint:
	$(PYTHON) -m pylint src/firebench_adapter_wrf_sfire --rcfile=.pylintrc

update-lint-score:
	$(PYTHON) .github/actions/run_pylint.py

code-formatting:
	$(PYTHON) -m black --check src/firebench_adapter_wrf_sfire tests .github/actions

fix-code-formatting:
	$(PYTHON) -m black src/firebench_adapter_wrf_sfire tests .github/actions

bandit:
	$(PYTHON) -m bandit -r src/firebench_adapter_wrf_sfire --severity-level high --confidence-level high

update-docs-changelog:
	$(PYTHON) .github/actions/update_changelog_in_docs.py

docs:
	$(PYTHON) -m sphinx -b html docs docs/_build/html

clean-build:
	rm -rf build
	rm -rf dist
	rm -rf *.egg-info
	find . -type d -name "*.egg-info" -prune -exec rm -rf {} +

install-build-tools:
	$(PYTHON) -m pip install --upgrade build twine

build: clean-build
	$(PYTHON) -m build

check-dist: build
	$(PYTHON) -m twine check dist/*

upload-test: check-dist
	$(PYTHON) -m twine upload --repository testpypi dist/*

upload: check-dist
	$(PYTHON) -m twine upload dist/*

clean:
	rm -rf docs/_build