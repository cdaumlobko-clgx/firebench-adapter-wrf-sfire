from importlib.metadata import version, PackageNotFoundError
from .severity_mtbs import get_mtbs_severity_surf
from .building_damage import get_building_damage

try:
    __version__ = version("firebench-adapter-wrf-sfire")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = ["__version__"]
