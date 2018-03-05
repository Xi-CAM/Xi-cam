from pathlib import Path
from typing import Union, List

from databroker.utils import ALL
from databroker._core import Header
from warnings import warn


# extension_map = {EDFPlugin: ['edf']}

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
    from xicam.plugins import manager as pluginmanager # must be a late import
    # ext = Path(filename).suffix[1:]
    # for cls, extensions in extension_map.items():
    #     if ext in extensions:
    handlercandidates = []
    ext = Path(uris[0]).suffix
    for plugin in pluginmanager.getPluginsOfCategory('DataHandlerPlugin'):
        if ext in plugin.plugin_object.DEFAULT_EXTENTIONS:
            handlercandidates.append(plugin)
    if not handlercandidates: return NonDBHeader({}, [], [], {})
    # try:
    return NonDBHeader(**handlercandidates[0].plugin_object.ingest(uris))
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

    def __init__(self, start: dict, descriptors: List[dict], events: List[dict], stop: dict):
        self.startdoc = start
        self.descriptordocs = descriptors
        self.eventdocs = events
        self.stopdoc = stop

    def __getitem__(self, k):
        try:
            return getattr(self, k)
        except AttributeError as e:
            raise KeyError(k)

    def get(self, *args, **kwargs):
        return getattr(self, *args, **kwargs)

    def items(self):
        for k in self.keys():
            yield k, getattr(self, k)

    def values(self):
        for k in self.keys():
            yield getattr(self, k)

    def keys(self):
        for k in ('start', 'descriptors', 'events', 'stop'):
            yield k

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
        return self.descriptordocs

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
        return {key for event in self['eventdocs'] for key in event['data'].keys()}

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
            if stream_name is ALL or stream_name == d.get('name', 'primary'):
                result.update(d['object_keys'])
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
        for d in sorted(self.descriptors, key=lambda d: d['time']):
            config = d['configuration'].get(device_name)
            if config:
                result[d['name']].append(config['data'])
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
        yield self.start
        yield self.descriptors
        yield self.events
        yield self.stop

    def stream(self, *args, **kwargs):
        warn("The 'stream' method been renamed to 'documents'. The old name "
             "will be removed in the future.")
        yield from self.documents(*args, **kwargs)

    def table(self, stream_name='primary', fields=None, fill=False,
              timezone=None, convert_times=True, localize_times=True):
        '''
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
        '''
        raise NotImplementedError

    def events(self, stream_name='primary', fields=None, fill=False):
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

        for ev in self.eventdocs:
            if not set(fields).isdisjoint(set(ev['data'].keys())) or not fields:
                yield ev

    def data(self, field, stream_name='primary', fill=True):
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
        for event in self.events(stream_name=stream_name,
                                 fields=[field],
                                 fill=fill):
            yield event['data'][field].asarray()

    def meta_array(self, field=None):
        return DocMetaArray(self, field)

from functools import lru_cache
import numpy as np

class DocMetaArray(object):
    def __init__(self, header: NonDBHeader, field=None):
        if not field:
            fields = []
        else:
            fields = [field]
        self.events = list(header.events(fields=fields))
        if not field: field = list(self.events[0]['data'].keys())[0]
        self.field = field
        firstslice = self.slice(0)
        self.dtype = firstslice.dtype
        self.len = len(list(self.events))
        self.shape = (self.len, *firstslice.shape)
        self.ndim = firstslice.ndim + 1
        self.size = firstslice.size * self.len

    def min(self):
        return self._min

    def max(self):
        return self._max

    def slice(self, i):
        arr = self.events[i]['data'][self.field].asarray()
        self._min = arr.min()
        self._max = arr.max()
        return arr

    def __getitem__(self, item: Union[List[slice], int]):
        if isinstance(item, list) and len(item)>1:
            rmin = item[0].start if item[0].start is not None else 0
            rmax = item[0].stop if item[0].stop is not None else self.shape[0]
            rstep = item[0].step if item[0].step is not None else 1
            r = range(rmin, rmax, rstep)
            return np.array([self.slice(i)[item[1:]] for i in r])
        return self.slice(item)

    def transpose(self,ax):
        if ax != [0,1,2]:
            raise ValueError('A DocMetaArray cannot actually be transposed; the transpose method is provided for '
                             'compatibility with pyqtgraph''s ImageView')
        return self

    def __len__(self):
        return self.len


class lazyfield(object):
    def __init__(self, handler, *args, **kwargs):
        self.handler = handler
        self.args = args
        self.kwargs = kwargs
        super(lazyfield, self).__init__()

    def implements(self, t):
        if t == 'MetaArray': return True

    def asarray(self):
        return self.handler()(*self.args, **self.kwargs)

# TODO: Eliminate lazyfield and use only handler in doc?



