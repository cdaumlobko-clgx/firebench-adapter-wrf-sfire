import numpy as np
import hdf5plugin
import h5py
from netCDF4 import Dataset
import firebench.standardize as fs
import firebench.tools as ft
from datetime import datetime, timedelta
import geopandas as gpd
from pathlib import Path
from os.path import getsize


def get_perimeters_from_t_ign_g(
    new_h5: h5py.File,
    obs_h5: h5py.File,
    wrf_dataset: Dataset,
    list_perimeter_paths: list[str],
    t_ign_g_ref_time: str,
    fire_grid_bound: int = 25,
    overwrite: bool = False,
):
    KML_DIR = "kml"
    Path(KML_DIR).mkdir(parents=True, exist_ok=True)
    origin = datetime.fromisoformat(t_ign_g_ref_time)

    xlat = np.array(
        wrf_dataset["FXLAT"][0, fire_grid_bound:-fire_grid_bound, fire_grid_bound:-fire_grid_bound]
    )
    xlon = np.array(
        wrf_dataset["FXLONG"][0, fire_grid_bound:-fire_grid_bound, fire_grid_bound:-fire_grid_bound]
    )
    t_ign_g = wrf_dataset["TIGN_G"][-1, fire_grid_bound:-fire_grid_bound, fire_grid_bound:-fire_grid_bound]

    for perim_path in list_perimeter_paths:
        obs_datetime = datetime.fromisoformat(obs_h5[perim_path].attrs["time"])
        time_s = (obs_datetime - origin).total_seconds()
        print(f"Perimeter {perim_path} after {time_s} s")
        sfire_kml_path = Path(
            f"{KML_DIR}", f"SFIRE_{fs.sanitize_iso8601(fs.datetime_to_iso8601(obs_datetime))}.kml"
        )
        if not sfire_kml_path.exists() or overwrite:
            sfire_kml_filename = sfire_kml_path.resolve()
            perim_sfire = ft.array_to_geopolygons(t_ign_g, xlon, xlat, time_s)
            perim_sfire.to_file(sfire_kml_filename, driver="KML", layer="fire_perimeter")
        else:
            print(
                "KML file already found in directory and reused. Use overwrite = True to recompute perimeter."
            )

        grp = new_h5.create_group(perim_path)
        grp.attrs["time"] = fs.datetime_to_iso8601(obs_datetime)
        grp.attrs["rel_path"] = sfire_kml_filename
        grp.attrs["sha256"] = ft.calculate_sha256(sfire_kml_filename)
        grp.attrs["file_size_bytes"] = getsize(sfire_kml_filename)
