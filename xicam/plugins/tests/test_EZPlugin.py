import pytest
from pytestqt import qtbot


def test_EZPlugin(qtbot):
    from xicam.plugins import EZPlugin
    from xicam.gui.static import path
    from xicam.core.data import NonDBHeader

    def runtest():
        import numpy as np

        img = np.random.random((100, 100, 100))
        EZTest.instance.setImage(img)

        hist = np.histogram(img, 100)
        EZTest.instance.plot(hist[1][:-1], hist[0])

    def appendcatalog(header: NonDBHeader):
        img = header.meta_array(list(header.fields())[0])
        EZTest.instance.setImage(img)

    EZTest = EZPlugin(
        name="EZTest",
        toolbuttons=[(str(path("icons/calibrate.png")), runtest)],
        parameters=[{"name": "Test", "value": 10, "type": "int"}, {"name": "Fooo", "value": True, "type": "bool"}],
        appendcatalog=appendcatalog,
    )
    return EZTest

