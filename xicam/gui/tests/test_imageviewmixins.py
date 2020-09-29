from pytestqt import qtbot


def test_logIntensity(qtbot):
    from xicam.gui.widgets.imageviewmixins import LogScaleIntensity
    import numpy as np

    windows = []

    data1 = np.fromfunction(lambda x, y: np.exp((x ** 2 + y ** 2) / 10000.0), (100, 100)) - 2
    data2 = np.random.random((100, 100))
    data3 = np.random.random((100, 100)) * 1000 - 2
    data3[:10, :10] = np.random.random((10, 10)) * 10 - 2

    for data in [data1, data2, data3]:
        w = LogScaleIntensity()
        w.setImage(data)
        w.show()
        windows.append(w)


def test_xarrayview(qtbot):
    from xicam.gui.widgets.imageviewmixins import XArrayView
    from xarray import DataArray
    import numpy as np

    data = np.random.random((100, 10, 10,))
    xdata = DataArray(data, dims=['E (eV)', 'y (μm)', 'x (μm)'], coords=[np.arange(100)*100, np.arange(10)/10., np.arange(10)/10.])

    w = XArrayView()

    w.setImage(xdata)

    w.show()
    # qtbot.stopForInteraction()


def test_betterlayout(qtbot):
    from xicam.gui.widgets.imageviewmixins import BetterLayout
    from xarray import DataArray
    import numpy as np

    data = np.random.random((10, 10,))

    w = BetterLayout()

    w.setImage(data)

    w.show()
    #qtbot.stopForInteraction()