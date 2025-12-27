from importlib.metadata import version, PackageNotFoundError

from .building_damage import get_building_damage
from .perimeters import get_perimeter_from_t_ign_g
from .ravg import get_ravg_cc
from .severity_mtbs import get_mtbs_severity_surf

try:
    __version__ = version("firebench-adapter-wrf-sfire")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = ["__version__"]
