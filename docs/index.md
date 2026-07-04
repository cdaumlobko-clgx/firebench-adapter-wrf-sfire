# firebench-adapter-wrf-sfire

`firebench-adapter-wrf-sfire` converts native WRF-SFIRE output into FireBench-standardized HDF5 datasets. It is distributed separately from FireBench because it is specific to one model, while FireBench provides the shared benchmark format, metrics, and adapter utilities.

The adapter reads WRF-SFIRE netCDF output, samples or interpolates model fields onto FireBench observation grids, and writes standardized groups that can be used by FireBench benchmark workflows.

```{toctree}
:maxdepth: 1

installation.md
tutorials/index.md
api/index.rst
changelog.md
license.md
```