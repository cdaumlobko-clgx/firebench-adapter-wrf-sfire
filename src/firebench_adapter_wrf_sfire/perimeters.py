import numpy as np
import hdf5plugin
import h5py
from netCDF4 import Dataset
import firebench.standardize as fs
import firebench.tools as ft
from datetime import datetime, timezone
import geopandas as gpd
from pathlib import Path
from os.path import getsize


def _as_utc_datetime(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc)


def _validate_matching_timezone(*datetimes: datetime):
    has_tz = [dt.tzinfo is not None for dt in datetimes]
    if any(has_tz) and not all(has_tz):
        raise ValueError(
            "Cannot mix timezone-aware and timezone-naive datetimes. "
            "Use UTC consistently for t_ign_g_ref_time and perimeter times."
        )


def _valid_tign_g_values(t_ign_g: np.ndarray) -> np.ndarray:
    values = np.asarray(t_ign_g, dtype=np.float64)
    return values[np.isfinite(values)]


def _validate_kml_has_polygons(kml_path: Path):
    perimeters = gpd.read_file(kml_path, driver="KML")
    if perimeters.empty:
        raise ValueError(
            f"KML perimeter file contains no polygons: {kml_path}. "
            "Delete it or rerun with overwrite=True to recompute it."
        )


def get_perimeters_from_t_ign_g(
    new_h5: h5py.File,
    obs_h5: h5py.File,
    wrf_dataset: Dataset,
    list_perimeter_paths: list[str],
    t_ign_g_ref_time: str,
    fire_grid_bound: int = 25,
    kml_dir: str = "kml",
    overwrite: bool = False,
):
    Path(kml_dir).mkdir(parents=True, exist_ok=True)
    origin_raw = datetime.fromisoformat(t_ign_g_ref_time.replace("Z", "+00:00"))
    origin = _as_utc_datetime(origin_raw)

    xlat = np.array(
        wrf_dataset["FXLAT"][
            0, fire_grid_bound:-fire_grid_bound, fire_grid_bound:-fire_grid_bound
        ]
    )
    xlon = np.array(
        wrf_dataset["FXLONG"][
            0, fire_grid_bound:-fire_grid_bound, fire_grid_bound:-fire_grid_bound
        ]
    )
    t_ign_g = wrf_dataset["TIGN_G"][
        -1, fire_grid_bound:-fire_grid_bound, fire_grid_bound:-fire_grid_bound
    ]
    valid_t_ign_g = _valid_tign_g_values(t_ign_g)
    if valid_t_ign_g.size == 0:
        raise ValueError("TIGN_G contains no finite values in the selected fire grid.")
    min_t_ign_g = float(np.min(valid_t_ign_g))
    max_t_ign_g = float(np.max(valid_t_ign_g))

    for perim_path in list_perimeter_paths:
        obs_datetime_raw = datetime.fromisoformat(
            obs_h5[perim_path].attrs["time"].replace("Z", "+00:00")
        )
        obs_datetime = _as_utc_datetime(obs_datetime_raw)
        _validate_matching_timezone(origin_raw, obs_datetime_raw)
        time_s = (obs_datetime - origin).total_seconds()
        print(
            f"Perimeter {perim_path} after {time_s} s "
            f"(TIGN_G finite range: {min_t_ign_g} to {max_t_ign_g} s)"
        )
        sfire_kml_path = Path(
            f"{kml_dir}",
            f"SFIRE_{fs.sanitize_iso8601(fs.datetime_to_iso8601(obs_datetime_raw))}.kml",
        )
        sfire_kml_filename = sfire_kml_path.resolve()
        if not sfire_kml_filename.exists() or overwrite:
            if time_s < min_t_ign_g or time_s > max_t_ign_g:
                raise ValueError(
                    f"Perimeter time {time_s} s for {perim_path} is outside the finite TIGN_G range "
                    f"[{min_t_ign_g}, {max_t_ign_g}] s. Check t_ign_g_ref_time and timezone synchronization."
                )
            perim_sfire = ft.array_to_geopolygons(t_ign_g, xlon, xlat, time_s)
            if perim_sfire.empty:
                raise ValueError(
                    f"No polygon extracted for {perim_path} at {time_s} s. "
                    "Check t_ign_g_ref_time, timezone synchronization, fire_grid_bound, and TIGN_G units."
                )
            perim_sfire.to_file(
                sfire_kml_filename, driver="KML", layer="fire_perimeter"
            )
        else:
            print(
                "KML file already found in directory and reused. Use overwrite = True to recompute perimeter."
            )
            _validate_kml_has_polygons(sfire_kml_filename)

        grp = new_h5.create_group(perim_path)
        grp.attrs["time"] = fs.datetime_to_iso8601(obs_datetime_raw)
        grp.attrs["rel_path"] = sfire_kml_path.as_posix()
        grp.attrs["sha256"] = ft.calculate_sha256(sfire_kml_filename)
        grp.attrs["file_size_bytes"] = getsize(sfire_kml_filename)
