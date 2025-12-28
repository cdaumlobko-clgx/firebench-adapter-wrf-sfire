import numpy as np
import hdf5plugin
import h5py
from netCDF4 import Dataset
import firebench.standardize as fs
from datetime import datetime
from firebench import Quantity, svn
from bisect import bisect_left, bisect_right
from firebench_adapter_common.interpolation import find_nearest_grid_point
from scipy.interpolate import interp1d


def _read_station_time_origin(obs_h5: h5py.File, station_path: str) -> datetime:
    """Read station time origin as datetime from HDF5 attributes."""
    station = obs_h5[station_path]
    return datetime.fromisoformat(station["time"].attrs["time_origin"])


def _station_time_vector_seconds(obs_h5: h5py.File, station_path: str) -> np.ndarray:
    """Return station 'time' vector converted to seconds (float64)."""
    station = obs_h5[station_path]
    time_raw = np.array(station["time"][:])
    time_units = station["time"].attrs["time_units"]
    return Quantity(time_raw, time_units).to("s").magnitude.astype(np.float64)


def _period_offsets_seconds(
    dt_origin: datetime, start_dt: datetime, end_dt: datetime
) -> tuple[float, float]:
    """Compute (start, end) offsets in seconds relative to dt_origin."""
    offset_start = (start_dt - dt_origin).total_seconds()
    offset_end = (end_dt - dt_origin).total_seconds()
    return offset_start, offset_end


def _mask_between_inclusive(x: np.ndarray, x0: float, x1: float) -> np.ndarray:
    """Boolean mask for x0 <= x <= x1 (inclusive)."""
    return (x >= x0) & (x <= x1)


def _time_in_period_seconds(
    obs_h5: h5py.File,
    station_path: str,
    period_start_dt: datetime,
    period_end_dt: datetime,
) -> np.ndarray:
    """
    Equivalent to __get_time_vector_s: station time in seconds filtered to a period window.
    """
    dt_origin = _read_station_time_origin(obs_h5, station_path)
    time_vec_s = _station_time_vector_seconds(obs_h5, station_path)
    offset_start, offset_end = _period_offsets_seconds(dt_origin, period_start_dt, period_end_dt)
    return time_vec_s[_mask_between_inclusive(time_vec_s, offset_start, offset_end)].astype(np.float64)


def _sfire_time_seconds(wrf_dataset: Dataset, offset_start_s: float) -> np.ndarray:
    """
    Compute SFIRE time in seconds relative to the period start.
    Matches existing logic: XTIME (min) -> seconds, then subtract offset_start.
    """
    xtime_min = np.array(wrf_dataset["XTIME"][:], dtype=np.float64)
    return Quantity(xtime_min, "min").to("s").magnitude - offset_start_s


def _bracket_indices_inclusive(model_time: np.ndarray, ref_start: float, ref_end: float):
    """
    Find indices that frame [ref_start, ref_end] using the same bisect logic:
      i_start = last index with model_time[i] <= ref_start
      i_end   = first index with model_time[i] >= ref_end
    """
    i_start = bisect_right(model_time, ref_start) - 1
    i_end = bisect_left(model_time, ref_end)
    return i_start, i_end


def _validate_bracket(i_start: int, i_end: int, model_time_len: int):
    """Raise if bracket falls outside model time range (same as existing check)."""
    if i_start < 0 or i_end >= model_time_len:
        raise ValueError("Reference time outside model time range")


def _create_station_group_with_attrs(
    new_h5: h5py.File,
    obs_h5: h5py.File,
    station_path: str,
    attrs_to_copy: list[str],
) -> h5py.Group:
    """Create station group and copy select attributes if present."""
    new_grp = new_h5.create_group(station_path)
    src_attrs = obs_h5[station_path].attrs
    for attr in attrs_to_copy:
        if attr in src_attrs.keys():
            new_grp.attrs[attr] = src_attrs[attr]
    return new_grp


def _write_time_dataset_seconds(
    grp: h5py.Group,
    time_s: np.ndarray,
    period_start_dt: datetime,
    compression_lvl: int,
) -> h5py.Dataset:
    """Create 'time' dataset with standard attrs (origin + units)."""
    ds = grp.create_dataset("time", data=time_s, **hdf5plugin.Zstd(clevel=compression_lvl))
    ds.attrs["time_origin"] = fs.datetime_to_iso8601(period_start_dt)
    ds.attrs["time_units"] = "s"


def _interp_linear_1d_strict(x: np.ndarray, y: np.ndarray, xq: np.ndarray) -> np.ndarray:
    """
    Linear interpolation with the same settings as your current usage:
    bounds_error=True, fill_value=np.nan, assume_sorted=True.
    """
    f = interp1d(
        x,
        y,
        kind="linear",
        bounds_error=True,
        fill_value=np.nan,
        assume_sorted=True,
    )
    return f(xq)


def __process_weather_station(
    new_h5: h5py.File,
    obs_h5: h5py.File,
    wrf_dataset: Dataset,
    station_path: str,
    sfire_ref_time: datetime,
    period_start_dt: datetime,
    period_end_dt: datetime,
    fire_grid_bound: int,
    compression_lvl: int,
):
    STATION_ATTRS_TO_COPY = [
        "position_lat",
        "position_lon",
        "position_lat_units",
        "position_lon_units",
    ]
    time_in_period = _time_in_period_seconds(obs_h5, station_path, period_start_dt, period_end_dt)
    if len(time_in_period) == 0:
        print("No data in time period. Skip")
        return

    # SFIRE time
    offset_start = (period_start_dt - sfire_ref_time).total_seconds()
    time_sfire = _sfire_time_seconds(wrf_dataset, offset_start)
    i_start, i_end = _bracket_indices_inclusive(time_sfire, time_in_period[0], time_in_period[-1])
    _validate_bracket(i_start, i_end, len(time_sfire))

    # Add time to new group
    new_wx = _create_station_group_with_attrs(new_h5, obs_h5, station_path, STATION_ATTRS_TO_COPY)
    _write_time_dataset_seconds(new_wx, time_in_period, period_start_dt, compression_lvl)

    # get SFIRE data
    xlat = np.array(
        wrf_dataset["XLAT"][0, fire_grid_bound:-fire_grid_bound, fire_grid_bound:-fire_grid_bound]
    )
    xlon = np.array(
        wrf_dataset["XLONG"][0, fire_grid_bound:-fire_grid_bound, fire_grid_bound:-fire_grid_bound]
    )
    Ny, Nx = xlat.shape
    min_dlat = np.min(np.diff(xlat, axis=0))
    min_dlon = np.min(np.diff(xlon, axis=1))

    station = obs_h5[station_path]
    if svn.AIR_TEMPERATURE.value in station.keys():
        print("Process air temperature")
        # Verify T2
        if np.isclose(
            Quantity(
                float(obs_h5[f"{station_path}/{svn.AIR_TEMPERATURE.value}"].attrs["sensor_height"]),
                obs_h5[f"{station_path}/{svn.AIR_TEMPERATURE.value}"].attrs["sensor_height_units"],
            )
            .to("m")
            .magnitude,
            2,
            atol=0.1,
        ):
            print("Nearest T2")
            i_nearest, j_nearest = find_nearest_grid_point(
                Nx,
                Ny,
                obs_h5[station_path].attrs["position_lat"],
                obs_h5[station_path].attrs["position_lon"],
                xlat,
                xlon,
                min_dlat,
                min_dlon,
            )
            sfire_t2_interp = _interp_linear_1d_strict(
                time_sfire[i_start : i_end + 1],
                wrf_dataset["T2"][i_start : i_end + 1, j_nearest, i_nearest],
                time_in_period,
            )
            var = new_wx.create_dataset(
                svn.AIR_TEMPERATURE.value, data=sfire_t2_interp, **hdf5plugin.Zstd(clevel=compression_lvl)
            )
            var.attrs["units"] = "degK"


def get_weather_stations(
    new_h5: h5py.File,
    obs_h5: h5py.File,
    wrf_dataset: Dataset,
    sfire_ref_time: str,
    period_start_dt: datetime,
    period_end_dt: datetime,
    fire_grid_bound: int = 25,
    compression_lvl: int = 3,
):
    origin = datetime.fromisoformat(sfire_ref_time)
    for ts in obs_h5[f"{fs.TIME_SERIES}"].keys():
        if ts.startswith("station_"):
            print(f"Process {ts}")
            __process_weather_station(
                new_h5,
                obs_h5,
                wrf_dataset,
                f"{fs.TIME_SERIES}/{ts}",
                origin,
                period_start_dt,
                period_end_dt,
                fire_grid_bound,
                compression_lvl,
            )
