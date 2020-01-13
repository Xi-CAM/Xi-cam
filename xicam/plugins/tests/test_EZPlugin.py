
import pytest


@pytest.yield_fixture(autouse=True)
def with_QApplication():
    # Code that will run before your test
    from qtpy.QtWidgets import QApplication

    app = QApplication([])
    # A test function will be run at this point
    yield app
    # Code that will run after your test, for example:
    # ... do something to check the existing files
    # assert QApplication.exec_() == 0


def test_EZPlugin():
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


if __name__ == '__main__':
    from qtpy.QtWidgets import QApplication

    app = QApplication([])
    import run_xicam
    from xicam.plugins import EZPlugin
    from xicam.gui.static import path
    from xicam.core.data import NonDBHeader

    plugin = test_EZPlugin()
    run_xicam.main()

    app.exec_()
