import h5py
import numpy as np
from netCDF4 import Dataset

import firebench_adapter_wrf_sfire as adapter
from firebench_adapter_wrf_sfire import (
    get_building_damage,
    get_mtbs_severity_surf,
    get_perimeters_from_t_ign_g,
    get_ravg_cc,
    get_weather_stations,
)


def test_public_api_exports_documented_functions():
    assert callable(get_building_damage)
    assert callable(get_mtbs_severity_surf)
    assert callable(get_perimeters_from_t_ign_g)
    assert callable(get_ravg_cc)
    assert callable(get_weather_stations)

    for name in (
        "get_building_damage",
        "get_mtbs_severity_surf",
        "get_perimeters_from_t_ign_g",
        "get_ravg_cc",
        "get_weather_stations",
    ):
        assert name in adapter.__all__


def test_version_is_available():
    assert isinstance(adapter.__version__, str)
    assert adapter.__version__


def test_mtbs_severity_synthetic_regression(tmp_path):
    wrf_path = tmp_path / "wrfout.nc"
    obs_path = tmp_path / "obs.h5"
    out_path = tmp_path / "model.h5"
    group_path = "/spatial_2d/Caldor_MTBS"

    with Dataset(wrf_path, "w") as wrf:
        wrf.createDimension("Time", 1)
        wrf.createDimension("south_north", 2)
        wrf.createDimension("west_east", 2)

        dims = ("Time", "south_north", "west_east")
        xlat = wrf.createVariable("FXLAT", "f8", dims)
        xlon = wrf.createVariable("FXLONG", "f8", dims)
        fuel_frac = wrf.createVariable("FUEL_FRAC", "f8", dims)

        xlat[0, :, :] = np.array([[38.0, 38.0], [39.0, 39.0]])
        xlon[0, :, :] = np.array([[-121.0, -120.0], [-121.0, -120.0]])
        fuel_frac[0, :, :] = np.array([[0.1, 0.5], [0.7, 0.9]])

    with h5py.File(obs_path, "w") as obs_h5:
        group = obs_h5.create_group(group_path)
        group.attrs["crs"] = "EPSG:4326"
        group.create_dataset("position_lat", data=np.array([[38.0, 38.0], [39.0, 39.0]]))
        group.create_dataset("position_lon", data=np.array([[-121.0, -120.0], [-121.0, -120.0]]))

    with h5py.File(out_path, "w") as new_h5, h5py.File(obs_path, "r") as obs_h5, Dataset(
        wrf_path, "r"
    ) as wrf:
        get_mtbs_severity_surf(
            new_h5,
            obs_h5,
            group_path,
            wrf,
            fire_grid_bound=0,
            compression_lvl=1,
        )

    with h5py.File(out_path, "r") as out_h5:
        result = out_h5[f"{group_path}/fire_burn_severity"][:, :]
        np.testing.assert_array_equal(result, np.array([[4, 3], [2, 1]]))
        assert out_h5[group_path].attrs["crs"] == "EPSG:4326"