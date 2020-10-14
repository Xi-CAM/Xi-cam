from pytestqt import qtbot
from qtpy.QtWidgets import QApplication
import dask.array as da
from xarray import DataArray
import numpy as np
import pytest
from xicam.core.data import load_header
from xicam.plugins import manager as plugin_manager


size = 100


@pytest.fixture
def complex_big_data():
    return DataArray(da.fromfunction(lambda y, x, E, T, t: (y + x) * np.cos(E/10) + T + t ** 2,
                                     shape=(size, size, size, size, size),
                                     chunks=10,
                                     dtype=float),
                     dims=['y (μm)', 'x (μm)', 'E (eV)', 'T (K)', 't (s)'],
                     coords=[np.arange(size) / 10.,
                             np.arange(size) / 10.,
                             np.arange(size) * 100,
                             np.arange(size) / 10.,
                             np.arange(size) / 10.])


@pytest.fixture
def simple_small_data():
    size = 10
    return DataArray(da.fromfunction(lambda y, x, E, T, t: (y + x) * np.cos(E/10) + T + t ** 2,
                                     shape=(size, size, size, size, size),
                                     chunks=10,
                                     dtype=float),
                     dims=['y (μm)', 'x (μm)', 'E (eV)', 'T (K)', 't (s)'],
                     coords=[np.arange(size) / 10.+10,
                             np.arange(size) / 1.+1,
                             np.arange(size) * 10+10,
                             np.arange(size) * 100.,
                             np.arange(size) * 1000.])


def project_arpes(catalog):
    # TODO: single-source
    ENERGY_FIELD = 'E (eV)'
    SAMPLE_X_FIELD = 'Sample X (um)'
    SAMPLE_Y_FIELD = 'Sample Y (um)'
    ANGLE_FIELD = '???'

    data = catalog.primary.to_dask()
    raw_data = data['raw'][0]
    raw_data = raw_data.assign_coords({name:np.asarray(data[name][0]) for name in [SAMPLE_Y_FIELD, SAMPLE_X_FIELD, ANGLE_FIELD, ENERGY_FIELD]})
    return raw_data


@pytest.fixture
def arpes_data():
    plugin_manager.collect_plugins()
    required_task = next(filter(lambda task: task.name=='application/x-fits', plugin_manager._tasks))
    plugin_manager._load_plugin(required_task)
    plugin_manager._instantiate_plugin(required_task)
    # FIXME: don't rely on absolute file path here!
    catalog = load_header(['C:\\Users\\LBL\\PycharmProjects\\merged-repo\\Xi-cam.spectral\\xicam\\spectral\\ingestors\\20161214_00034.fits'])
    data = project_arpes(catalog)
    return data


def test_NDViewer(simple_small_data, qtbot):
    from xicam.gui.widgets.ndimageview import NDImageView
    from skimage.transform import rescale, resize, downscale_local_mean


    w = NDImageView()
    w.histogram_subsampling_axes = ['E (eV)']
    w.setData(simple_small_data)

    qtbot.addWidget(w)
    # qtbot.stopForInteraction()

# @pytest.fixture
# def xarray_catalog():
#     import time
#     import event_model
#     def catalog_generator():
#         data = np.ones((10,10,10))
#
#         energy = np.arange(data.shape[2])
#         sample_x = np.arange(data.shape[1])
#         sample_y = np.arange(data.shape[0])
#
#         xarray = DataArray(data, dims=['y (μm)', 'x (μm)', 'E (eV)'], coords=[sample_y, sample_x, energy])
#
#         # Compose run start
#         run_bundle = event_model.compose_run()  # type: event_model.ComposeRunBundle
#         start_doc = run_bundle.start_doc
#         yield 'start', start_doc
#
#         # Compose descriptor
#         source = 'nxSTXM'
#         frame_data_keys = {'raw': {'source': source,
#                                    'dtype': 'number',
#                                    'dims': xarray.dims,
#                                    # 'coords': [energy, sample_y, sample_x],
#                                    'shape': data.shape}}
#         frame_stream_name = 'primary'
#         frame_stream_bundle = run_bundle.compose_descriptor(data_keys=frame_data_keys,
#                                                             name=frame_stream_name,
#                                                             # configuration=_metadata(path)
#                                                             )
#         yield 'descriptor', frame_stream_bundle.descriptor_doc
#
#         yield 'event', frame_stream_bundle.compose_event(data={'raw': xarray},
#                                                          timestamps={'raw': time.time()})
#
#         yield 'stop', run_bundle.compose_stop()
#
#     return catalog_generator
#
#
# def test_xarray_mixed_state(xarray_catalog):
#     from databroker.in_memory import BlueskyInMemoryCatalog
#     docs = list(xarray_catalog())
#     uid = docs[0][1]["uid"]
#     catalog = BlueskyInMemoryCatalog()
#     catalog.upsert(docs[0][1], docs[-1][1], xarray_catalog, [], {})
#
#     data = catalog[uid].primary.to_dask()['raw']
#
#     # FIXME: Unexpected failure, since data.indexes has been wiped out by databroker
#     with pytest.raises(Exception) as exc:
#         assert data.sel({'E (eV)': 0}, method='nearest') is not None
#
#     assert list(data.indexes.keys()) == ['time']
#
#     # NOTE: However, we can put data.indexes back together, since databroker doesn't touch data.coords
#     data = data.reindex({dim: data.coords[dim] for dim in data.dims})
#
#     assert list(data.indexes.keys()) == ['time', 'y (μm)', 'x (μm)', 'E (eV)']
#
#     assert data.sel({'E (eV)': 0}, method='nearest') is not None
