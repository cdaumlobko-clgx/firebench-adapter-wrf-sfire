# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1-dev1] - 2026-08-07

### Added
- Add the YAML-driven `fb-sfire run` CLI with validation and configurable processing sections.
- Add regression coverage for CLI workflows and relative perimeter asset references.

### Changed
- Resolve relative input, output, and KML paths from the directory containing the YAML configuration.
- Update the Caldor tutorial to document the CLI workflow and v2026.2 benchmark paths.
- Allow adapter functions to reuse an open WRF netCDF dataset across processing sections.

### Fixed
- Use `/polygons` for Caldor v2026.2 perimeter groups instead of the obsolete `/geopolygons` path.
- Store generated KML references relative to the output HDF5 file, as required by FireBench integrity checks.

## [0.1-dev0] - 2026-07-07

### Added
- Add the `firebench-adapter-wrf-sfire` package for converting native WRF-SFIRE netCDF outputs into FireBench-standardized datasets.
- Add building damage processing from WRF-SFIRE `FIRE_AREA` outputs using nearest-grid lookup.
- Add perimeter generation from `TIGN_G`, including KML output reuse, configurable KML directories, relative output paths, file size metadata, and SHA-256 metadata.
- Add RAVG canopy-cover-loss processing from `FIRE_AREA` and `CFB`, with nearest-neighbor interpolation onto the observation grid.
- Add MTBS burn-severity processing from `FUEL_FRAC`, with configurable severity thresholds and nearest-neighbor interpolation.
- Add weather-station processing for air temperature, relative humidity, wind direction, wind speed, and 10-hour fuel moisture content.
- Add weather-station time-window filtering, SFIRE time bracketing, sensor-height checks, and wind-speed extrapolation using surface roughness.
- Add package metadata, developer dependencies, Makefile targets, pylint support, and README installation notes.

### Changed
- Depend on FireBench directly for shared adapter utilities through `firebench.adapter_common`.
- Use compressed HDF5 datasets for generated FireBench-standardized outputs.
- Export adapter entry points from `firebench_adapter_wrf_sfire.__init__`.

### Fixed
- Preserve weather-station time origins when writing filtered station output.
- Use the atmospheric grid for weather variables and include the end index when slicing model time brackets.
- Store generated perimeter paths in POSIX form and avoid absolute paths in FireBench metadata.
- Reuse existing perimeter KML files unless `overwrite=True`.

[Unreleased]: https://github.com/wirc-sjsu/firebench-adapter-wrf-sfire/compare/0.1-dev1...HEAD
[0.1-dev1]: https://github.com/wirc-sjsu/firebench-adapter-wrf-sfire/compare/0.1-dev0...0.1-dev1
[0.1-dev0]: https://github.com/wirc-sjsu/firebench-adapter-wrf-sfire/releases/tag/0.1-dev0
