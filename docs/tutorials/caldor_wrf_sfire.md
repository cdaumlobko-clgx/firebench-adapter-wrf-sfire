# Convert WRF-SFIRE Output To A FireBench Standard File

This tutorial shows the main workflow for converting WRF-SFIRE output into a FireBench-standardized HDF5 file. The example is based on a Caldor Fire workflow.

The script uses two inputs:

- a FireBench observation/reference file, for example `/path/to/firebench-data/Caldor.h5`
- a WRF-SFIRE netCDF output file, for example `/path/to/wrf-sfire/wrfout`

It writes a new standardized model-output file, for example `outputs/SFIRE_Caldor.h5`.

## Processing Flags

Each processing flag controls one standardized output product:

- `process_severity`: converts WRF-SFIRE `FUEL_FRAC` into an MTBS-style burn severity surface.
- `process_bd`: samples WRF-SFIRE `FIRE_AREA` at building locations to estimate building damage.
- `process_ravg_cc`: converts `FIRE_AREA` and `CFB` into a RAVG canopy-cover-loss surface.
- `process_perims`: extracts fire perimeters from `TIGN_G` and stores KML metadata.
- `process_wx`: samples and standardizes weather-station variables.

## Example Script

```python
from datetime import datetime

import h5py
import pytz
from netCDF4 import Dataset

import firebench.standardize as fs
from firebench_adapter_wrf_sfire import (
    get_building_damage,
    get_mtbs_severity_surf,
    get_perimeters_from_t_ign_g,
    get_ravg_cc,
    get_weather_stations,
)


caldor_datapath = "/path/to/firebench-data/Caldor.h5"
caldor_wrf = "/path/to/wrf-sfire/wrfout"
output_path = "outputs/SFIRE_Caldor.h5"

process_severity = False
process_bd = False
process_ravg_cc = False
process_perims = True
process_wx = False

list_perimeters = [
    f"/{fs.GEOPOLYGONS}/Caldor_2021-08-20T20:20-07:00",
    f"/{fs.GEOPOLYGONS}/Caldor_2021-08-21T21:15-07:00",
]

sfire_ref_time = "2021-08-21T00:00-00:00"

tz = pytz.timezone("UTC")
start_dt = tz.localize(datetime(2021, 8, 21, 0, 0))
end_dt = tz.localize(datetime(2021, 8, 23, 0, 0))

new_h5 = fs.new_std_file(
    output_path,
    "Aurelien Costes, SJSU; Collaborator Name, Institution;",
    overwrite=True,
)

try:
    with h5py.File(caldor_datapath, "r") as obs_h5, Dataset(caldor_wrf, "r") as wrf_dataset:
        if process_severity:
            print("process Burn Severity")
            get_mtbs_severity_surf(
                new_h5,
                obs_h5,
                "/spatial_2d/Caldor_MTBS",
                wrf_dataset,
                compression_lvl=20,
            )

        if process_bd:
            print("process Building Damage")
            get_building_damage(
                new_h5,
                obs_h5,
                "points/building_damaged",
                wrf_dataset,
                compression_lvl=20,
            )

        if process_ravg_cc:
            print("process RAVG Canopy Cover Loss")
            get_ravg_cc(
                new_h5,
                obs_h5,
                "/spatial_2d/ravg_cc",
                wrf_dataset,
                compression_lvl=20,
            )

        if process_perims:
            print("process Perimeters")
            get_perimeters_from_t_ign_g(
                new_h5,
                obs_h5,
                wrf_dataset,
                list_perimeters,
                sfire_ref_time,
                kml_dir="outputs/Cawfe_kml",
                overwrite=True,
                extraction_method="tign_g",
                smooth_sigma=10,
            )

        if process_wx:
            print("Process WX")
            get_weather_stations(
                new_h5,
                obs_h5,
                wrf_dataset,
                sfire_ref_time,
                start_dt,
                end_dt,
            )
finally:
    new_h5.close()
```

## Notes

The perimeter workflow requires the perimeter groups in the observation file to have a `time` attribute. The value of `sfire_ref_time` must use the same timezone convention as those perimeter times so that `TIGN_G` is converted to the correct elapsed seconds.

The example only enables perimeter processing by default. Enable the other flags when the corresponding reference groups exist in the FireBench observation file and the required WRF-SFIRE variables are present in the model output.