import h5py
import numpy as np
from click.testing import CliRunner
from netCDF4 import Dataset

from firebench_adapter_wrf_sfire.cli import main


def _write_text(path, content):
    path.write_text(content, encoding="utf-8")


def _create_synthetic_severity_inputs(tmp_path):
    wrf_path = tmp_path / "wrfout.nc"
    obs_path = tmp_path / "obs.h5"
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

    return obs_path, wrf_path, group_path


def test_cli_requires_main_section(tmp_path):
    config_path = tmp_path / "config.yml"
    _write_text(config_path, "severity:\n  enabled: true\n")

    result = CliRunner().invoke(main, ["run", str(config_path)])

    assert result.exit_code != 0
    assert "main section is required" in result.output


def test_cli_requires_enabled_processing_section(tmp_path):
    config_path = tmp_path / "config.yml"
    _write_text(config_path, "main: {}\n")

    result = CliRunner().invoke(main, ["run", str(config_path)])

    assert result.exit_code != 0
    assert "At least one processing section" in result.output


def test_cli_rejects_naive_weather_datetime(tmp_path):
    obs_path = tmp_path / "obs.h5"
    wrf_path = tmp_path / "wrfout.nc"
    obs_path.touch()
    wrf_path.touch()
    config_path = tmp_path / "config.yml"
    _write_text(
        config_path,
        f"""
main:
  obs_path: {obs_path}
  wrf_path: {wrf_path}
  output_path: {tmp_path / "out.h5"}
  authors: Test Author
  sfire_ref_time: "2021-08-21T00:00:00+00:00"
  start_dt: "2021-08-21T00:00:00"
  end_dt: "2021-08-23T00:00:00+00:00"
weather:
  enabled: true
""",
    )

    result = CliRunner().invoke(main, ["run", str(config_path)])

    assert result.exit_code != 0
    assert "main.start_dt must include a timezone offset" in result.output


def test_cli_rejects_existing_output_without_overwrite(tmp_path):
    obs_path = tmp_path / "obs.h5"
    wrf_path = tmp_path / "wrfout.nc"
    output_path = tmp_path / "out.h5"
    obs_path.touch()
    wrf_path.touch()
    output_path.touch()
    config_path = tmp_path / "config.yml"
    _write_text(
        config_path,
        f"""
main:
  obs_path: {obs_path}
  wrf_path: {wrf_path}
  output_path: {output_path}
  authors: Test Author
severity:
  enabled: true
  group_path: /spatial_2d/Caldor_MTBS
""",
    )

    result = CliRunner().invoke(main, ["run", str(config_path)])

    assert result.exit_code != 0
    assert "Output file already exists" in result.output


def test_cli_runs_severity_from_relative_config_paths(tmp_path):
    obs_path, wrf_path, group_path = _create_synthetic_severity_inputs(tmp_path)
    config_path = tmp_path / "config.yml"
    output_path = tmp_path / "outputs" / "model.h5"
    _write_text(
        config_path,
        f"""
main:
  obs_path: {obs_path.name}
  wrf_path: {wrf_path.name}
  output_path: outputs/model.h5
  authors: Test Author
  overwrite: true
  compression_lvl: 1
  fire_grid_bound: 0
severity:
  enabled: true
  group_path: {group_path}
""",
    )

    result = CliRunner().invoke(main, ["run", str(config_path)])

    assert result.exit_code == 0, result.output
    assert f"Wrote {output_path}" in result.output
    with h5py.File(output_path, "r") as out_h5:
        result_data = out_h5[f"{group_path}/fire_burn_severity"][:, :]
        np.testing.assert_array_equal(result_data, np.array([[4, 3], [2, 1]]))
        assert out_h5.attrs["created_by"] == "Test Author"
