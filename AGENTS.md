# Repository Guidelines

## Project Structure & Module Organization

This repository is a Python package that adapts WRF-SFIRE outputs into FireBench-standardized datasets. Source code lives in `src/firebench_adapter_wrf_sfire/`, with one module per output domain such as `perimeters.py`, `severity_mtbs.py`, `building_damage.py`, `ravg.py`, and `wx.py`. Public package exports are managed in `src/firebench_adapter_wrf_sfire/__init__.py`.

Regression tests are in `tests/regression/`. Documentation is built with Sphinx from `docs/`, with tutorials under `docs/tutorials/` and API pages under `docs/api/`. Packaging and tool configuration are in `pyproject.toml`; common workflows are exposed through `Makefile`.

## Build, Test, and Development Commands

- `pip install -e ".[dev]"`: install the package locally with development tools.
- `make test`: run the pytest suite under `tests/`.
- `make test-cov`: run tests with coverage for `src/firebench_adapter_wrf_sfire`.
- `make code-formatting`: check Black formatting for source, tests, and action scripts.
- `make fix-code-formatting`: apply Black formatting.
- `make lint`: run Pylint using `.pylintrc`.
- `make bandit`: run high-severity, high-confidence Bandit checks.
- `make docs`: build HTML documentation into `docs/_build/html`.
- `make check-dist`: build the package and validate distributions with Twine.

## Coding Style & Naming Conventions

Use Python 3.10+ syntax and 4-space indentation. Black is the formatting authority, configured with a 108-character line length in `pyproject.toml`. Prefer clear, descriptive function names that match the package’s public API pattern, such as `get_perimeters_from_t_ign_g` or `get_weather_stations`. Keep modules focused on one output type or transformation.

## Testing Guidelines

Tests use `pytest`; place new regression coverage under `tests/regression/` and name files `test_*.py`. Test functions should be behavior-focused, for example `test_public_api_exports_documented_functions`. For data-heavy code, prefer compact synthetic fixtures using `tmp_path`, `h5py`, and `netCDF4` rather than checked-in generated files. Run `make test` before submitting changes, and use `make test-cov` for changes touching shared conversion logic.

## Commit & Pull Request Guidelines

Recent commit messages are short, imperative summaries such as `Fix SFIRE perimeter extraction when raw TIGN_G contour is empty` or `add default values for cosalpha, sinalpha`. Keep commits focused and describe the observable change.

Pull requests should include a concise description, the affected adapter functions or modules, test results, and any documentation updates. Link related issues when available. For changes that alter output datasets, include the benchmark group or variable names affected.
