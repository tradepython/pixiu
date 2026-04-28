
from importlib.metadata import PackageNotFoundError, version


try:
    __version__ = version("pixiu")
except PackageNotFoundError:
    __version__ = "unknown"
