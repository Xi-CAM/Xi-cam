from yapsy.IPlugin import IPlugin
import uuid
import datetime
from typing import Tuple,List
from xicam.core.data import lazyfield


class DataHandlerPlugin(IPlugin):
    """
    This base class defines a reader/writer for an on-disk file format. This interface will be structured such that the
    format definition is registered with FabIO at activation, and will mirror the FabIO API structure. Subclass
    instances should not depend on other plugins. Example: A reader/writer for the *.fits file format.

    See the FabIO API for a detailed explanation of the file format abstraction.

    See xicam.plugins.tests for examples.

    """

    DESCRIPTION = ""

    DEFAULT_EXTENTIONS = []

    MAGIC_NUMBERS = []

    Handler = None

    @staticmethod
    def ingest(paths):
        return NotImplementedError


def start_doc(start_uid: str, metadata: dict = None):
    if not metadata: metadata = {}
    metadata.update({'uid': start_uid,
                     'time': datetime.datetime.now().strftime('%a %b %d %H:%M:%S %Y')})
    return metadata


def event_doc(data_uid: str, descriptor_uid: str, metadata: dict = None):
    if not metadata: metadata = {}
    metadata.update({'descriptor': descriptor_uid,
                     'time': datetime.datetime.now().strftime('%a %b %d %H:%M:%S %Y'),
                     'uid': str(uuid.uuid4()),
                     'data': {'image': data_uid}})
    return metadata


def embedded_local_event_doc(descriptor_uid: str,
                             field: str,
                             handler: type,
                             handler_args: tuple = None,
                             handler_kwargs: dict = None,
                             metadata: dict = None):
    if not handler_args: handler_args = tuple()
    if not handler_kwargs: handler_kwargs = {}
    if not metadata: metadata = {}

    datafield = {field:lazyfield(handler, *handler_args, **handler_kwargs)}
    metadata.update(FillableDict({'descriptor': descriptor_uid,
                                  'time': datetime.datetime.now(),
                                  'uid': str(uuid.uuid4()),
                                  'data': datafield}))
    return metadata


def descriptor_doc(start_uid: str, descriptor_uid: str, metadata: dict = None):
    if not metadata: metadata = {}
    metadata.update({'run_start': start_uid,
                     'name': 'primary',
                     'uid': descriptor_uid})
    return metadata


def stop_doc(start_uid: str, metadata: dict = None):
    if not metadata: metadata = {}
    metadata.update({'run_start': start_uid,
                     'time': 0,  # TODO: set this to the cumulative time of the full doc
                     'uid': str(uuid.uuid4()),
                     'exit_status': 'success'})
    return metadata


class FillableDict(dict):
    def __init__(self, *args, **kwargs):
        super(FillableDict, self).__init__(*args, **kwargs)
        self.filled = False

    def fill(self):
        self.update({'data': self['data']['handler'](*self['data']['args'], **self['data']['kwargs'])})
        self.filled = True

