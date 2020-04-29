from .plugin import PluginType
import uuid
import datetime
from typing import Tuple, List
from xicam.core.data import lazyfield
from pathlib import Path

# Note: Split into DataHandlerPlugin and IngestorPlugin?


class DataHandlerPlugin(PluginType):
    """
    This base class defines a reader/writer for an on-disk file format. This interface will be structured such that the
    format definition is registered with FabIO at activation, and will mirror the FabIO API structure. Subclass
    instances should not depend on other plugins. Example: A reader/writer for the *.fits file format.

    See the FabIO API for a detailed explanation of the file format abstraction.

    See xicam.plugins.tests for examples.

    """

    is_singleton = False
    needs_qt = False

    DESCRIPTION = ""

    DEFAULT_EXTENTIONS = []

    MAGIC_NUMBERS = []

    def __call__(self, *args, **kwargs):
        raise NotImplementedError

    @classmethod
    def getStartDoc(cls, paths, start_uid):
        metadata = cls.parseTXTFile(paths[0])
        metadata.update(cls.parseDataFile(paths[0]))
        descriptor_keys = getattr(cls, "descriptor_keys", [])
        metadata = dict([(key, metadata.get(key)) for key in descriptor_keys])
        return start_doc(start_uid=start_uid)

    @classmethod
    def getEventDocs(cls, paths, descriptor_uid):
        shape = cls(paths[0])().shape  # Assumes each frame has same shape
        for path in paths:
            metadata = cls.parseTXTFile(path)
            metadata.update(cls.parseDataFile(path))
            yield embedded_local_event_doc(descriptor_uid, "primary", cls, (path,), metadata=metadata)

    @staticmethod
    def getDescriptorUIDs(paths):
        return str(uuid.uuid4())

    @classmethod
    def getDescriptorDocs(cls, paths, start_uid, descriptor_uid):
        metadata = cls.parseTXTFile(paths[0])
        metadata.update(cls.parseDataFile(paths[0]))

        metadata = dict([(key, metadata.get(key, None)) for key in getattr(cls, "descriptor_keys", [])])
        yield descriptor_doc(start_uid, descriptor_uid, metadata=metadata)

    @classmethod
    def getStopDoc(cls, paths, start_uid):
        return stop_doc(start_uid=start_uid)

    @classmethod
    def reduce_paths(cls, paths):
        return paths

    @classmethod
    def title(cls, paths):
        if len(paths) > 1:
            return f"Series: {Path(paths[0]).resolve().stem}…"
        return Path(paths[0]).resolve().stem

    @classmethod
    def _setTitle(cls, startdoc, paths):
        startdoc["sample_name"] = cls.title(paths)
        return startdoc

    @classmethod
    def ingest(cls, paths):
        paths = cls.reduce_paths(paths)
        start_uid = str(uuid.uuid4())
        descriptor_uids = cls.getDescriptorUIDs(paths)
        return {
            "start": cls._setTitle(cls.getStartDoc(paths, start_uid), paths),
            "descriptors": list(cls.getDescriptorDocs(paths, start_uid, descriptor_uids)),
            "events": list(cls.getEventDocs(paths, descriptor_uids)),
            "stop": cls.getStopDoc(paths, start_uid),
        }

    def parseTXTFile(self, *args, **kwargs):
        return {}

    def parseDataFile(self, *args, **kwargs):
        return {}


def start_doc(start_uid: str, metadata: dict = None):
    if not metadata:
        metadata = {}
    metadata.update({"uid": start_uid, "time": datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Y")})
    return metadata


def event_doc(data_uid: str, descriptor_uid: str, metadata: dict = None):
    if not metadata:
        metadata = {}
    metadata.update(
        {
            "descriptor": descriptor_uid,
            "time": datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Y"),
            "uid": str(uuid.uuid4()),
            "data": {"primary": data_uid},
        }
    )
    return metadata


def embedded_local_event_doc(
    descriptor_uid: str,
    field: str,
    handler: type,
    resource_path: tuple = None,
    resource_kwargs: dict = None,
    metadata: dict = None,
):
    if not resource_kwargs:
        resource_kwargs = {}
    if not metadata:
        metadata = {}

    datafield = {field: lazyfield(handler, resource_path, resource_kwargs)}
    metadata.update(
        FillableDict(
            {"descriptor": descriptor_uid, "time": datetime.datetime.now(), "uid": str(uuid.uuid4()), "data": datafield}
        )
    )
    return metadata


def descriptor_doc(start_uid: str, descriptor_uid: str, metadata: dict = None):
    if not metadata:
        metadata = {}
    metadata.update({"run_start": start_uid, "name": "primary", "uid": descriptor_uid})
    return metadata


def stop_doc(start_uid: str, metadata: dict = None):
    if not metadata:
        metadata = {}
    metadata.update(
        {
            "run_start": start_uid,
            "time": 0,  # TODO: set this to the cumulative time of the full doc
            "uid": str(uuid.uuid4()),
            "exit_status": "success",
        }
    )
    return metadata


class FillableDict(dict):
    def __init__(self, *args, **kwargs):
        super(FillableDict, self).__init__(*args, **kwargs)
        self.filled = False

    def fill(self):
        self.update({"data": self["data"]["handler"](*self["data"]["args"], **self["data"]["kwargs"])})
        self.filled = True
