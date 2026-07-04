# Installation

Install the released package from PyPI:

```bash
pip install firebench-adapter-wrf-sfire
```

For local development, clone the repository and install the package with development dependencies:

```bash
git clone https://github.com/wirc-sjsu/firebench-adapter-wrf-sfire.git
cd firebench-adapter-wrf-sfire
pip install -e ".[dev]"
```

The adapter depends on FireBench and common scientific Python packages used for HDF5, netCDF, and geospatial processing.