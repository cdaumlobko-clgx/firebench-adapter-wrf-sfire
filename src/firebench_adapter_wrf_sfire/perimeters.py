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

PERIMETER_EXTRACTION_METHOD_TIGN_G = "tign_g"
PERIMETER_EXTRACTION_METHOD_BURNED_MASK = "burned_mask"
PERIMETER_EXTRACTION_METHODS = (
    PERIMETER_EXTRACTION_METHOD_TIGN_G,
    PERIMETER_EXTRACTION_METHOD_BURNED_MASK,
)


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
    masked_values = np.ma.masked_invalid(t_ign_g)
    return np.asarray(masked_values.compressed(), dtype=np.float64)


def _valid_tign_g_mask_and_values(t_ign_g: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    masked_values = np.ma.masked_invalid(t_ign_g)
    values = np.asarray(masked_values.filled(np.nan), dtype=np.float64)
    valid_mask = ~np.ma.getmaskarray(masked_values) & np.isfinite(values)
    return valid_mask, values


def _validate_kml_has_polygons(kml_path: Path):
    perimeters = gpd.read_file(kml_path, driver="KML")
    if perimeters.empty:
        raise ValueError(
            f"KML perimeter file contains no polygons: {kml_path}. "
            "Delete it or rerun with overwrite=True to recompute it."
        )


def _perimeter_extraction_summary(
    t_ign_g: np.ndarray,
    xlon: np.ndarray,
    xlat: np.ndarray,
    time_s: float,
) -> str:
    finite, values = _valid_tign_g_mask_and_values(t_ign_g)
    burned = finite & (values <= time_s)
    finite_count = int(np.sum(finite))
    burned_count = int(np.sum(burned))
    boundary_count = 0
    if burned_count:
        boundary = np.zeros_like(burned, dtype=bool)
        boundary[0, :] = True
        boundary[-1, :] = True
        boundary[:, 0] = True
        boundary[:, -1] = True
        boundary_count = int(np.sum(burned & boundary))

    finite_values = values[finite]
    percentiles = (
        np.percentile(finite_values, [1, 5, 50, 95, 99]) if finite_count else []
    )
    percentile_text = ", ".join(f"{value:.1f}" for value in percentiles)
    return (
        f"finite_cells={finite_count}, cells_le_iso={burned_count}, "
        f"boundary_cells_le_iso={boundary_count}, "
        f"TIGN_G_percentiles_1_5_50_95_99=[{percentile_text}], "
        f"lon_range=[{float(np.nanmin(xlon))}, {float(np.nanmax(xlon))}], "
        f"lat_range=[{float(np.nanmin(xlat))}, {float(np.nanmax(xlat))}]"
    )


def _burned_mask_field(t_ign_g: np.ndarray, time_s: float) -> np.ndarray:
    finite, values = _valid_tign_g_mask_and_values(t_ign_g)
    return (finite & (values <= time_s)).astype(float)


def _extract_perimeter_geopolygons(
    t_ign_g: np.ndarray,
    xlon: np.ndarray,
    xlat: np.ndarray,
    time_s: float,
    extraction_method: str,
    smooth_sigma: float,
) -> gpd.GeoDataFrame:
    if extraction_method == PERIMETER_EXTRACTION_METHOD_TIGN_G:
        return ft.array_to_geopolygons(
            t_ign_g, xlon, xlat, time_s, smooth_sigma=smooth_sigma
        )

    if extraction_method == PERIMETER_EXTRACTION_METHOD_BURNED_MASK:
        burned_field = _burned_mask_field(t_ign_g, time_s)
        return ft.array_to_geopolygons(
            burned_field, xlon, xlat, 0.5, smooth_sigma=smooth_sigma
        )

    raise ValueError(
        f"Unknown perimeter extraction method {extraction_method!r}. "
        f"Available methods: {', '.join(PERIMETER_EXTRACTION_METHODS)}"
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
    extraction_method: str = PERIMETER_EXTRACTION_METHOD_TIGN_G,
    smooth_sigma: float = 0,
):
    if extraction_method not in PERIMETER_EXTRACTION_METHODS:
        raise ValueError(
            f"Unknown perimeter extraction method {extraction_method!r}. "
            f"Available methods: {', '.join(PERIMETER_EXTRACTION_METHODS)}"
        )
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
            f"(TIGN_G finite range: {min_t_ign_g} to {max_t_ign_g} s, "
            f"method={extraction_method}, smooth_sigma={smooth_sigma})"
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
            perim_sfire = _extract_perimeter_geopolygons(
                t_ign_g, xlon, xlat, time_s, extraction_method, smooth_sigma
            )
            if perim_sfire.empty:
                extraction_summary = _perimeter_extraction_summary(
                    t_ign_g, xlon, xlat, time_s
                )
                raise ValueError(
                    f"No polygon extracted for {perim_path} at {time_s} s. "
                    f"method={extraction_method}, smooth_sigma={smooth_sigma}. "
                    f"{extraction_summary}. "
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
