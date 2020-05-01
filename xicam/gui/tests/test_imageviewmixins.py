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



if __name__ == "__main__":
    test_logIntensity()
