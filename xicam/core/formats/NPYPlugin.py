import mimetypes

from bluesky_live.run_builder import RunBuilder
from xicam.plugins.datahandlerplugin import DataHandlerPlugin, start_doc
import numpy as np

mimetypes.add_type('application/x-npy', '.npy')


def ingest_npy(paths):
    d = np.load(paths[0], allow_pickle=True)
    data_keys = {'image': {'source': paths[0],
                           'dtype': 'array',
                           'shape': d.shape}}

    with RunBuilder() as builder:
        builder.add_stream("primary",
                           # NOTE: Put data in list, since Runbuilder.add_stream expects
                           # a sequence number to add event_page
                           data={'image': [d]},
                           data_keys=data_keys
                           )

    builder.get_run()
    yield from builder._cache


class NPYPlugin(DataHandlerPlugin):
    name = "NPYPlugin"

    DEFAULT_EXTENTIONS = [".npy"]

    def __call__(self, *args, **kwargs):
        return np.load(self.path, allow_pickle=True)

    def __init__(self, path):
        super(NPYPlugin, self).__init__()
        self.path = path

    @classmethod
    def getStartDoc(cls, paths, start_uid):
        return start_doc(start_uid=start_uid, metadata={"paths": paths})