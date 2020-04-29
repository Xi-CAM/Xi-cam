from . import patches  # explicitly load patches to other packages

from ._version import get_versions

__version__ = get_versions()["version"]
del get_versions
