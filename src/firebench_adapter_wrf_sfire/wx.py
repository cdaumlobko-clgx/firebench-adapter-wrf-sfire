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

def __get_time_vector_s(
    obs_h5: h5py.File,
    station_path: str,
    period_start_dt: datetime,
    period_end_dt: datetime,
):
    station = obs_h5[station_path]
    dt_origin = datetime.fromisoformat(station["time"].attrs["time_origin"])
    time_vec = Quantity(np.array(station["time"][:]), station["time"].attrs["time_units"]).to("s").magnitude
    offset_start = (period_start_dt - dt_origin).total_seconds()
    offset_end = (period_end_dt - dt_origin).total_seconds()
    return np.array([t for t in time_vec if t >= offset_start and t <= offset_end], dtype=np.float64)


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
    station_attr_copy = [
        "position_lat",
        "position_lon",
        "position_lat_units",
        "position_lon_units",
    ]
    time_in_period = __get_time_vector_s(obs_h5, station_path, period_start_dt, period_end_dt)

    if len(time_in_period) == 0:
        print("No data in time period. Skip")
        return

    # SFIRE time
    offset_start = (period_start_dt - sfire_ref_time).total_seconds()
    time_sfire = (
        Quantity(np.array(wrf_dataset["XTIME"][:], dtype=np.float64), "min").to("s").magnitude
        - offset_start
    )
    i_start = bisect_right(time_sfire, time_in_period[0]) - 1
    i_end = bisect_left(time_sfire, time_in_period[-1])

    if i_start < 0 or i_end >= len(time_sfire):
        raise ValueError("Reference time outside model time range")

    new_wx = new_h5.create_group(station_path)
    for attr in station_attr_copy:
        if attr in obs_h5[station_path].attrs.keys():
            new_wx.attrs[attr] = obs_h5[station_path].attrs[attr]

    var = new_wx.create_dataset(
            "time", data=time_in_period, **hdf5plugin.Zstd(clevel=compression_lvl)
        )
    var.attrs["time_origin"] = fs.datetime_to_iso8601(period_start_dt)
    var.attrs["time_units"] = "s"

    # get SFIRE data
    xlat = np.array(
        wrf_dataset["FXLAT"][0, fire_grid_bound:-fire_grid_bound, fire_grid_bound:-fire_grid_bound]
    )
    xlon = np.array(
        wrf_dataset["FXLONG"][0, fire_grid_bound:-fire_grid_bound, fire_grid_bound:-fire_grid_bound]
    )
    Ny, Nx = xlat.shape
    min_dlat = np.min(np.diff(xlat, axis=0))
    min_dlon = np.min(np.diff(xlon, axis=1))

    station = obs_h5[station_path]
    if svn.AIR_TEMPERATURE.value in station.keys():
        print("Process air temperature")
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
        sfire_raw_t2 = wrf_dataset["T2"][i_start: i_end, j_nearest, i_nearest]
        f = interp1d(
            time_sfire[i_start:i_end], sfire_raw_t2,
            kind="linear",
            bounds_error=True,
            fill_value=np.nan,   # or "extrapolate"
            assume_sorted=True
        )
        sfire_t2_interp = f(time_in_period)
        new_wx.create_dataset(
            svn.AIR_TEMPERATURE.value, data=sfire_t2_interp, **hdf5plugin.Zstd(clevel=compression_lvl)
        )
        var.attrs["units"] = "degC"



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
