import numpy as np
import hdf5plugin
import h5py
from netCDF4 import Dataset
import firebench.standardize as fs
import firebench.tools as ft
from datetime import datetime, timedelta
from pathlib import Path
from firebench import Quantity, svn


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

def __process_T():
    pass

def __process_weather_station(
    new_h5: h5py.File,
    obs_h5: h5py.File,
    wrf_dataset: Dataset,
    station_path: str,
    period_start_dt: datetime,
    period_end_dt: datetime,
    fire_grid_bound: int,
):
    time_in_period = __get_time_vector_s(obs_h5, station_path, period_start_dt, period_end_dt)
    
    station = obs_h5[station_path]
    if svn.AIR_TEMPERATURE.value in station.keys():
        print("Process air temperature")


def get_weather_stations(
    new_h5: h5py.File,
    obs_h5: h5py.File,
    wrf_dataset: Dataset,
    period_start_dt: datetime,
    period_end_dt: datetime,
    fire_grid_bound: int = 25,
):
    for ts in obs_h5[f"{fs.TIME_SERIES}"].keys():
        if ts.startswith("station_"):
            print(f"Process {ts}")
            __process_weather_station(
                new_h5,
                obs_h5,
                wrf_dataset,
                f"{fs.TIME_SERIES}/{ts}",
                period_start_dt,
                period_end_dt,
                fire_grid_bound,
            )
