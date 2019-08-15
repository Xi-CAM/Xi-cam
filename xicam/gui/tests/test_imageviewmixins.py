def test_logIntensity():
    from xicam.gui.widgets.imageviewmixins import LogScaleIntensity
    import numpy as np
    from qtpy.QtWidgets import QApplication
    import pyqtgraph as pg
    import fabio

    app = QApplication([])

    windows = []

    data1 = np.fromfunction(lambda x, y: np.exp((x ** 2 + y ** 2) / 10000.0), (100, 100)) - 2
    data2 = fabio.open("/home/rp/data/YL1031/AGB_5S_USE_2_2m.edf").data
    data3 = np.random.random((100, 100)) * 1000 - 2
    data3[:10, :10] = np.random.random((10, 10)) * 10 - 2

    for data in [data1, data2, data3]:
        w = LogScaleIntensity()
        w.setImage(data)
        w.show()
        windows.append(w)

    app.exec_()


if __name__ == "__main__":
    test_logIntensity()
