from pathlib import Path
from typing import Union, List, Set

from qtpy.QtCore import Signal, QObject

from databroker.utils import ALL
from databroker.in_memory import BlueskyInMemoryCatalog
from warnings import warn

import mimetypes
import warnings

import entrypoints


def detect_mimetypes(filename: str) -> List[str]:
    """
    Take in a filename; return a mimetype string like 'image/tiff'.
    """
    # First rely on custom "sniffers" that can employ file signatures (magic
    # numbers) or any other format-specific tricks to extract a mimetype.
    matched_mimetypes = list()

    with open(filename, "rb") as file:
        # The choice of 64 bytes is arbitrary. We may increase this in the
        # future if we discover reason to. Therefore, sniffers should not
        # assume that they will receive this exact number of bytes.
        first_bytes = file.read(64)
    for ep in entrypoints.get_group_all("databroker.sniffers"):
        try:
            content_sniffer = ep.load()  # TODO: only load sniffers once
        except Exception as ex:
            msg.logError(ex)
        else:
            matched_mimetype = content_sniffer(filename, first_bytes)
            if matched_mimetype:
                matched_mimetypes.append(matched_mimetype)

    # Guessing the mimetype from the mimemtype db is quick, lets do it always
    matched_mimetype = mimetypes.guess_type(filename)[0]
    if matched_mimetype:
        matched_mimetypes.append(matched_mimetype)

    if not matched_mimetypes:
        raise UnknownFileType(f"Could not identify the MIME type of {filename}")

    return matched_mimetypes


def applicable_ingestors(filename, mimetype):
    """
    Take in a filename and its mimetype; return a list of compatible ingestors.
    """
    # Find ingestor(s) for this mimetype.
    ingestors = []
    for ep in entrypoints.get_group_all("databroker.ingestors"):
        if ep.name == mimetype:
            try:
                ingestor = ep.load()
            except Exception as ex:
                msg.logError(ex)
            else:
                ingestors.append(ingestor)

    return ingestors


def choose_ingestor(filename, mimetype):
    """
    Take in a filename and its mimetype; return an ingestor.
    If multiple are found, return the first one (deterministic but arbitrary).
    If none are found, raise.
    """
    ingestors = applicable_ingestors(filename, mimetype)
    if not ingestors:
        raise NoIngestor(f"No ingestors were applicable to {filename}")
    elif len(ingestors) > 1:
        warnings.warn("More than one ingestor was applicable.")
    return ingestors[0]


class UnknownFileType(ValueError):
    ...


class NoIngestor(ValueError):
    ...


def load_header(uris: List[Union[str, Path]] = None, uuid: str = None):
    """
    Load a document object, either from a file source or a databroker source, by uuid. If loading from a filename, the
    file will be registered in databroker.

    Parameters
    ----------
    uris
    uuid

    Returns
    -------
    NonDBHeader

    """
    from xicam.plugins import manager as pluginmanager  # must be a late import

    # ext = Path(filename).suffix[1:]
    # for cls, extensions in extension_map.items():
    #     if ext in extensions:

    # First try to see if we have a databroker ingestor, then fall-back to Xi-cam DataHandlers
    ingestor = None
    filename = str(Path(uris[0]))

    # Sanity checks
    if Path(filename).is_dir():
        msg.logMessage("Opening dir; nothing to load.")
        return

    if not Path(filename).exists():
        raise FileExistsError(f"Attempted to load non-existent file: {filename}")

    try:
        mimetypes = detect_mimetypes(filename)
    except UnknownFileType as ex:
        msg.logError(ex)
        mimetypes = []
    else:
        msg.logMessage(f"Mimetypes detected: {mimetypes}")

        # TODO: here, we try each valid mimetype; some GUI for selection will be needed

        for mimetype in mimetypes:
            try:
                ingestor = choose_ingestor(filename, mimetype)
            except NoIngestor as e:
                pass
            else:
                msg.logMessage(f"Ingestor selected: {ingestor}")
                break

    if ingestor:
        document = list(ingestor(uris))
        uid = document[0][1]["uid"]
        catalog = BlueskyInMemoryCatalog()
        # TODO -- change upsert signature to put start and stop as kwargs
        # TODO -- ask about more convenient way to get a BlueskyRun from a document generator
        catalog.upsert(document[0][1], document[-1][1], ingestor, [uris], {})
        return catalog[uid]
    else:
        warn(f"No applicable ingestor found. Falling-back to DataHandlers")

    handlercandidates = []
    ext = Path(uris[0]).suffix
    for plugin in pluginmanager.get_plugins_of_type("DataHandlerPlugin"):
        if ext in plugin.DEFAULT_EXTENTIONS:
            handlercandidates.append(plugin)
    if not handlercandidates:
        return NonDBHeader({}, [], [], {})
    # try:
    msg.logMessage(f"Handler selected: {handlercandidates[0]}")
    return NonDBHeader(**handlercandidates[0].ingest(uris))
    # except (IsADirectoryError, TypeError):
    #     # TODO: add Header ingestor for directory
    #     return NonDBHeader({}, [], [], {})


class NonDBHeader(object):
    """
    A dictionary-like object summarizing metadata for a run.
    """

    # def _repr_html_(self):
    #     env = jinja2.Environment()
    #     env.filters['human_time'] = _pretty_print_time
    #     template = env.from_string(_HTML_TEMPLATE)
    #     return template.render(document=self)

    ### dict-like methods ###

    def __init__(self, start: dict = None, descriptors: List[dict] = None, events: List[dict] = None, stop: dict = None):
        self._documents = {
            "start": [start] if start else [],
            "descriptor": descriptors or [],
            "event": events or [],
            "stop": [stop] if stop else [],
        }

    def append(self, docname, doc):
        if docname in ["start", "stop"] and self._documents[docname]:
            raise KeyError(f"A {docname} document already exists within this header.")
        self._documents[docname].append(doc)

    def __getitem__(self, k):
        try:
            return getattr(self, k)
        except AttributeError as e:
            raise KeyError(k)

    @property
    def startdoc(self):
        startdocs = self._documents["start"]
        return startdocs[0] if startdocs else {}

    @property
    def eventdocs(self):
        return self._documents["event"]

    @property
    def descriptordocs(self):
        return self._documents["descriptor"]

    def get(self, *args, **kwargs):
        return getattr(self, *args, **kwargs)

    def items(self):
        for k in self.keys():
            yield k, getattr(self, k)

    def values(self):
        for k in self.keys():
            yield getattr(self, k)

    def keys(self):
        yield from iter(self._documents.keys())

    # def to_name_dict_pair(self):
    #     ret = attr.asdict(self)
    #     ret.pop('db')
    #     ret.pop('_cache')
    #     ret['descriptors'] = self.descriptors
    #     return self._name, ret

    def __len__(self):
        return 4

    def __iter__(self):
        return self.keys()

    # ## convenience methods and properties, encapsulating one-liners ## #

    @property
    def descriptors(self):
        yield from self._documents["descriptor"]

    @property
    def stream_names(self):
        raise NotImplementedError

    def fields(self, stream_name=ALL):
        """
        Return the names of the fields ('data keys') in this run.

        Parameters
        ----------
        stream_name : string or ``ALL``, optional
            Filter results by stream name (e.g., 'primary', 'baseline'). The
            default, ``ALL``, combines results from all streams.

        Returns
        -------
        fields : set

        Examples
        --------
        Load the most recent run and list its fields.

        >>> h = db[-1]
        >>> h.fields()
        {'eiger_stats1_total', 'eiger_image'}

        See Also
        --------
        :meth:`Header.devices`
        """
        return {key for event in self["eventdocs"] for key in event["data"].keys()}

    def devices(self, stream_name=ALL):
        """
        Return the names of the devices in this run.

        Parameters
        ----------
        stream_name : string or ``ALL``, optional
            Filter results by stream name (e.g., 'primary', 'baseline'). The
            default, ``ALL``, combines results from all streams.

        Returns
        -------
        devices : set

        Examples
        --------
        Load the most recent run and list its devices.

        >>> h = db[-1]
        >>> h.devices()
        {'eiger'}

        See Also
        --------
        :meth:`Header.fields`
        """
        result = set()
        for d in self.descriptors:
            if stream_name is ALL or stream_name == d.get("name", "primary"):
                result.update(d["object_keys"])
        return result

    def config_data(self, device_name):
        """
        Extract device configuration data from Event Descriptors.

        This refers to the data obtained from ``device.read_configuration()``.

        See example below. The result is structed as a [...deep breath...]
        dictionary of lists of dictionaries because:

        * The device might have been read in multiple event streams
          ('primary', 'baseline', etc.). Each stream name is a key in the
          outer dictionary.
        * The configuration is typically read once per event stream, but in
          general may be read multiple times if the configuration is changed
          mid-stream. Thus, a list is needed.
        * Each device typically produces multiple configuration fields
          ('exposure_time', 'period', etc.). These are the keys of the inner
          dictionary.

        Parameters
        ----------
        device_name : string
            device name (originally obtained from the ``name`` attribute of
            some readable Device)

        Returns
        -------
        result : dict
            mapping each stream name (such as 'primary' or 'baseline') to a
            list of data dictionaries

        Examples
        --------
        Get the device configuration recorded for the device named 'eiger'.

        >>> h.config_data('eiger')
        {'primary': [{'exposure_time': 1.0}]}

        Assign the exposure time to a variable.

        >>> exp_time = h.config_data('eiger')['primary'][0]['exposure_time']

        How did we know that ``'eiger'`` was a valid argument? We can query for
        the complete list of device names:

        >>> h.device_names()
        {'eiger', 'cs700'}
        """
        result = defaultdict(list)
        for d in sorted(self.descriptors, key=lambda d: d["time"]):
            config = d["configuration"].get(device_name)
            if config:
                result[d["name"]].append(config["data"])
        return dict(result)  # strip off defaultdict behavior

    def documents(self, stream_name=ALL, fields=None, fill=False):
        """
        Load all documents from the run.

        This is a generator the yields ``(name, doc)``.

        Parameters
        ----------
        stream_name : string or ``ALL``, optional
            Filter results by stream name (e.g., 'primary', 'baseline'). The
            default, ``ALL``, combines results from all streams.
        fill : bool, optional
            Whether externally-stored data should be filled in. False by
            default.

        Yields
        ------
        name, doc : (string, dict)

        Examples
        --------
        Loop through the documents from a run.

        >>> h = db[-1]
        >>> for name, doc in h.headers():
        ...     # do something
        """
        for docname in self.keys():
            for doc in self._documents[docname]:
                yield docname, doc

    def stream(self, *args, **kwargs):
        warn("The 'stream' method been renamed to 'documents'. The old name " "will be removed in the future.")
        yield from self.documents(*args, **kwargs)

    def table(self, stream_name="primary", fields=None, fill=False, timezone=None, convert_times=True, localize_times=True):
        """
        Load the data from one event stream as a table (``pandas.DataFrame``).

        Parameters
        ----------
        stream_name : str, optional
            Get events from only "event stream" with this name.

            Default is 'primary'

        fields : List[str], optional
            whitelist of field names of interest; if None, all are returned

            Default is None

        fill : bool or Iterable[str], optional
            Which fields to fill.  If `True`, fill all
            possible fields.

            Each event will have the data filled for the intersection
            of it's external keys and the fields requested filled.

            Default is False

        handler_registry : dict, optional
            mapping filestore specs (strings) to handlers (callable classes)

        convert_times : bool, optional
            Whether to convert times from float (seconds since 1970) to
            numpy datetime64, using pandas. True by default.

        timezone : str, optional
            e.g., 'US/Eastern'; if None, use metadatastore configuration in
            `self.mds.config['timezone']`

        localize_times : bool, optional
            If the times should be localized to the 'local' time zone.  If
            True (the default) the time stamps are converted to the localtime
            zone (as configure in mds).

            This is problematic for several reasons:

              - apparent gaps or duplicate times around DST transitions
              - incompatibility with every other time stamp (which is in UTC)

            however, this makes the dataframe repr look nicer

            This implies convert_times.

            Defaults to True to preserve back-compatibility.

        Returns
        -------
        table : pandas.DataFrame

        Examples
        --------
        Load the 'primary' data stream from the most recent run into a table.

        >>> h = db[-1]
        >>> h.table()

        This is equivalent. (The default stream_name is 'primary'.)

        >>> h.table(stream_name='primary')
                                    time intensity
        0  2017-07-16 12:12:37.239582345       102
        1  2017-07-16 12:12:39.958385283       103

        Load the 'baseline' data stream.

        >>> h.table(stream_name='baseline')
                                    time temperature
        0  2017-07-16 12:12:35.128515999         273
        1  2017-07-16 12:12:40.128515999         274
        """
        raise NotImplementedError

    def events(self, stream_name="primary", fields=None, fill=False):
        """
        Load all Event documents from one event stream.

        This is a generator the yields Event documents.

        Parameters
        ----------
        stream_name : str, optional
            Get events from only "event stream" with this name.

            Default is 'primary'

        fields : List[str], optional
            whitelist of field names of interest; if None, all are returned

            Default is None

        fill : bool or Iterable[str], optional
            Which fields to fill.  If `True`, fill all
            possible fields.

            Each event will have the data filled for the intersection
            of it's external keys and the fields requested filled.

            Default is False

        Yields
        ------
        doc : dict

        Examples
        --------
        Loop through the Event documents from a run. This is 'lazy', meaning
        that only one Event at a time is loaded into memory.

        >>> h = db[-1]
        >>> for event in h.events():
        ...    # do something

        List the Events documents from a run, loading them all into memory at
        once.

        >>> events = list(h.events())
        # """
        # ev_gen = self.db.get_events([self], stream_name=stream_name,
        #                             fields=fields, fill=fill)

        for ev in self._documents["event"]:
            if not set(fields).isdisjoint(set(ev["data"].keys())) or not fields:
                yield ev

    def data(self, field, stream_name="primary", fill=True):
        """
        Extract data for one field. This is convenient for loading image data.

        Parameters
        ----------
        field : string
            such as 'image' or 'intensity'

        stream_name : string, optional
            Get data from a single "event stream." Default is 'primary'

        fill : bool, optional
             If the data should be filled.

        Yields
        ------
        data
        """
        if fill:
            fill = {field}
        for event in self.events(stream_name=stream_name, fields=[field], fill=fill):
            yield event["data"][field].asarray()

    def meta_array(self, field=None):
        return DocMetaArray(self, field)


class QNonDBHeader(QObject, NonDBHeader):
    sigChanged = Signal()

    def append(self, docname, doc):
        super(QNonDBHeader, self).append(docname, doc)
        self.sigChanged.emit()


from functools import lru_cache
import numpy as np
from xicam.core import msg


class MetaXArray(object):
    def __init__(self, dataarray):
        self.dataarray = dataarray

        for attr in ["size", "ndim", "shape", "dtype"]:
            setattr(self, attr, getattr(self.dataarray, attr))

    def __len__(self):
        return self.shape[0]

    def xvals(self):
        return range(len(self))

    def min(self):
        return self.dtype.type(self.dataarray.min())

    def max(self):
        return self.dtype.type(self.dataarray.max())

    def ravel(self):
        return self.dataarray.values.ravel()

    def __getitem__(self, item: Union[List[slice], int]):
        if isinstance(item, List):
            return np.asarray(self.dataarray[tuple(item)])
        else:
            return np.asarray(self.dataarray[item])

    def transpose(self, ax):
        if ax != [0, 1, 2]:
            raise ValueError(
                "A MetaXArray cannot actually be transposed; the transpose method is provided for "
                "compatibility with pyqtgraph"
                "s ImageView"
            )
        return self

    def view(self, _):
        return self

    def implements(self, _):
        return False


class DocMetaArray(object):
    def __init__(self, header: NonDBHeader, field: str = None):
        self._dtype = None
        self.header = header
        self._field = field
        self._events = None
        self._len = None
        self._shape = None
        self._size = None
        self._ndim = None

    @property
    def events(self):
        if not self._events:
            self._events = list(self.header.events(fields=[self.field]))
        return self._events

    def __len__(self):
        if not self._len:
            self._len = len(list(self.events))
        return self._len

    @property
    def size(self):
        if not self._size:
            self._size = self.slice(0).size * len(self)
        return self._size

    @property
    def ndim(self):
        if not self._ndim:
            self._ndim = self.slice(0).ndim + 1
        return self._ndim

    @property
    def shape(self):
        if not self._shape:
            self._shape = (len(self), *self.slice(0).shape)
        return self._shape

    @property
    def dtype(self):
        if not self._dtype:
            firstslice = self.slice(0)
            self._dtype = firstslice.dtype
        return self._dtype

    @property
    def field(self):
        if not self._field:
            fields = list(self.header.fields())
            if len(fields) > 1:
                msg.logError(
                    ValueError("Unspecified field for document stream with >1 field. Potentially unexpected behavior.")
                )
                self.field = next(iter(self.header.eventdocs[0]["data"].keys()))
            else:
                self.field = fields[0]

        return self._field

    @field.setter
    def field(self, value):
        self._field = value

    def min(self):
        if not self._min:
            # cache using slice
            self.slice(0)
        return self._min

    def max(self):
        if not self._max:
            # cache using slice
            self.slice(0)
        return self._max

    def slice(self, i):
        if not self.events:
            return None

        arr = self.events[i]["data"][self.field]
        if hasattr(arr, "asarray"):
            arr = arr.asarray()
        if not isinstance(arr, np.ndarray):
            arr = np.array(arr)
        self._min = arr.min()
        self._max = arr.max()
        return arr

    def __getitem__(self, item: Union[List[slice], int]):
        if isinstance(item, list) or isinstance(item, tuple) and len(item) > 1:
            rmin = item[0].start if item[0].start is not None else 0
            rmax = item[0].stop if item[0].stop is not None else self.shape[0]
            rstep = item[0].step if item[0].step is not None else 1
            r = range(rmin, rmax, rstep)
            return np.array([self.slice(i)[item[1:]] for i in r])
        return self.slice(item)

    def transpose(self, ax):
        # if ax != [0,1,2]:
        #     raise ValueError('A DocMetaArray cannot actually be transposed; the transpose method is provided for '
        #                      'compatibility with pyqtgraph''s ImageView')
        return self

    def view(self, _):
        return self


# TODO: Add asarray


class lazyfield(object):
    def __init__(self, handler_cls, resource_path, resource_kwargs):
        self.handler_cls = handler_cls
        self.resource_path = resource_path
        self.resource_kwargs = resource_kwargs
        self._handler = None
        super(lazyfield, self).__init__()

    @property
    def handler(self):
        if not self._handler:
            self._handler = self.handler_cls(*self.resource_path)
        return self._handler

    def implements(self, t):
        if t == "MetaArray":
            return True

    def asarray(self):
        return self.handler(**self.resource_kwargs)


# TODO: Eliminate lazyfield and use only handler in doc?
