import pytest


@pytest.yield_fixture(autouse=True)
def with_QApplication():
    # Code that will run before your test
    from qtpy.QtWidgets import QApplication

    app = QApplication([])
    # A test function will be run at this point
    yield
    # Code that will run after your test, for example:
    # ... do something to check the existing files
    # assert QApplication.exec_() == 0


def test_IProcessingPlugin():
    from ..processingplugin import ProcessingPlugin, Input, Output

    class SumProcessingPlugin(ProcessingPlugin):
        a = Input(default=1, units="nm", min=0)
        b = Input(default=2)
        c = Output()

        def evaluate(self):
            self.c.value = self.a.value + self.b.value
            return self.c.value

    t1 = SumProcessingPlugin()
    t2 = SumProcessingPlugin()
    assert t1.evaluate() == 3
    t1.a.value = 100
    assert t2.a.value == 1
    assert t1.inputs["a"].name == "a"
    assert t1.outputs["c"].name == "c"
    assert t1.outputs["c"].value == 3


def test_EZProcessingPlugin():
    from xicam.plugins import EZProcessingPlugin
    import numpy as np

    ArrayRotate = EZProcessingPlugin(np.rot90)
    assert ArrayRotate()
