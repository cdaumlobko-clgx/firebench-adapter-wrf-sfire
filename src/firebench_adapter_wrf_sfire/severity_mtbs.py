from numba import njit
import numpy as np
import hdf5plugin
import h5py
from netCDF4 import Dataset
from scipy.interpolate import NearestNDInterpolator
from firebench_adapter_common.interpolation import nearest_2d

# Threshold for burn severity
# <= SEVERITY_TH[0]: high (4)
# <= SEVERITY_TH[1]: moderate (3)
# <= SEVERITY_TH[2]: low (2)
# > SEVERITY_TH[2]: unburnt to low (1)
SEVERITY_TH_DEFAULT = np.array([0.2, 0.6, 0.8], dtype=np.float64)


@njit(fastmath=True)
def __compute_severity_from_fuel_frac(
    Nx: int, Ny: int, fuel_frac: np.ndarray, severity_thresholds: np.ndarray
):
    severity = np.zeros((Ny, Nx))
    for j in range(Ny):
        for i in range(Nx):
            if fuel_frac[j, i] <= severity_thresholds[0]:
                severity[j, i] = 4
            elif fuel_frac[j, i] <= severity_thresholds[1]:
                severity[j, i] = 3
            elif fuel_frac[j, i] <= severity_thresholds[2]:
                severity[j, i] = 2
            else:
                severity[j, i] = 1

    return severity


def get_mtbs_severity_surf(
    fb_h5: h5py.File,
    mtbs_group_path: str,
    wrf_dataset: Dataset,
    method: str = "fuel_frac",
    severity_thresholds: np.ndarray = SEVERITY_TH_DEFAULT,
    fire_grid_bound: int = 25,
):
    # get SFIRE data
    xlat = np.array(
        wrf_dataset["FXLAT"][0, fire_grid_bound:-fire_grid_bound, fire_grid_bound:-fire_grid_bound]
    )
    xlon = np.array(
        wrf_dataset["FXLONG"][0, fire_grid_bound:-fire_grid_bound, fire_grid_bound:-fire_grid_bound]
    )

    Ny, Nx = xlat.shape
    # get data from std file
    mtbs_lat = fb_h5[f"{mtbs_group_path}/position_lat"][:, :]
    mtbs_lon = fb_h5[f"{mtbs_group_path}/position_lon"][:, :]
    mtbs_crs = fb_h5[f"{mtbs_group_path}"].attrs["crs"]

    if method == "fuel_frac":
        fuel_frac = wrf_dataset["FUEL_FRAC"][
            -1, fire_grid_bound:-fire_grid_bound, fire_grid_bound:-fire_grid_bound
        ]
        SFIRE_severity = __compute_severity_from_fuel_frac(Nx, Ny, fuel_frac, severity_thresholds)
        return nearest_2d(
            SFIRE_severity, xlon, xlat, mtbs_lon, mtbs_lat
        )

    raise NotImplementedError(f"{method} not supported")
