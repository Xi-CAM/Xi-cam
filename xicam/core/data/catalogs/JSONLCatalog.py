from xicam.plugins import CatalogPlugin
from qtpy.QtWidgets import QFileDialog
import os
import glob
from pkg_resources import iter_entry_points

jsonCatalogType = None
for entry_point in iter_entry_points('intake.drivers'):
    if entry_point.name == 'bluesky-jsonl-catalog':
        jsonCatalogType = entry_point.load()
        break

else:
    raise ImportError('JSONLCatalog plugin unable to find JSONLCatalog type. Check databroker configuration.')

class JSONLCatalogPlugin(jsonCatalogType, CatalogPlugin):
    name = "JSONL"

    def __init__(self):
        # For proof of concept, this plugin will ask the user for a directory to load from
        dir = QFileDialog.getExistingDirectory(caption='Load JSONL from directory',
                                               directory=os.path.expanduser('~/'))

        # TODO: Move directory dialog to the controller

        paths = glob.glob(os.path.join(dir, '*.jsonl'))
        super(JSONLCatalogPlugin, self).__init__(paths)

        self.name = f"JSONL: {dir}"
