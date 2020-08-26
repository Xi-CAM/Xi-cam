from pytestqt import qtbot
import dask.array as da
from xarray import DataArray
import numpy as np
import pytest

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
    return DataArray(da.fromfunction(lambda y, x, E, T, t: (y + x + E + T + t),
                                     shape=(size, size, size, size, size),
                                     chunks=10,
                                     dtype=float),
                     dims=['y (μm)', 'x (μm)', 'E (eV)', 'T (K)', 't (s)'],
                     coords=[np.arange(size) / 10.,
                             np.arange(size) / 10.,
                             np.arange(size) * 100,
                             np.arange(size) / 10.,
                             np.arange(size) / 10.])


def test_NDViewer(complex_big_data, qtbot):
    from xicam.gui.widgets.ndimageview import NDImageView

    w = NDImageView()
    w.histogram_subsampling_axes = ['E (eV)', 't (s)']

    w.setData(complex_big_data)

    w.show()
    qtbot.stopForInteraction()
