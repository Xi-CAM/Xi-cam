from fabio.fabioimage import FabioImage
from yapsy.IPlugin import IPlugin


class FileFormatPlugin(FabioImage, IPlugin):
    """
    This base class defines a reader/writer for an on-disk file format. This interface will be structured such that the
    format definition is registered with FabIO at activation, and will mirror the FabIO API structure. Subclass
    instances should not depend on other plugins. Example: A reader/writer for the *.fits file format.

    See the FabIO API for a detailed explanation of the file format abstraction.

    See xicam.plugins.tests for examples.

    """

    DESCRIPTION = ""

    DEFAULT_EXTENTIONS = []

    RESERVED_HEADER_KEYS = []

    def _readheader(self, fname):
        raise NotImplementedError

    def read(self, fname, frame=None):
        raise NotImplementedError

    def write(self, fname):
        raise NotImplementedError
