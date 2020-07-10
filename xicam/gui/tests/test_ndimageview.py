from pytestqt import qtbot


def test_NDViewer(qtbot):
    from xicam.gui.widgets.ndimageview import NDImageView
    from xarray import DataArray
    import numpy as np

    data = np.fromfunction(lambda y, x, E, T, t: (y+x)*np.cos(E)+T+t**2,(10, 10, 10, 10, 10))
    xdata = DataArray(data,
                      dims=['y (μm)', 'x (μm)', 'E (eV)', 'T (K)', 't (s)'],
                      coords=[np.arange(10)/10., np.arange(10)/10., np.arange(10)*100, np.arange(10)/10., np.arange(10)/10.])

    w = NDImageView()

    w.setData(xdata)

    w.show()
    qtbot.stopForInteraction()