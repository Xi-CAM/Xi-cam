import numpy as np
import pytest
from pytestqt import qtbot
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QLabel
from xicam.gui.widgets.plotwidgetmixins import CurveLabels, BetterLayout, LogButtons, OffsetPlots


@pytest.fixture()
def plot_data():
    x = np.arange(10) + 1
    y = (np.arange(10) + 1) * 2
    y[::2] -= 1
    return x, y


def test_curveLabels(qtbot, plot_data):
    # Smoke test
    # TODO: better test (qtbot.mouseClick the items?)
    widget = CurveLabels()
    widget.plot(x=plot_data[0], y=plot_data[1])
    widget.show()


def test_betterlayout(qtbot, plot_data):
    widget = BetterLayout()
    widget.plot(x=plot_data[0], y=plot_data[1])
    widget.add_widget_to_bottom(QLabel("Bottom"))
    widget.add_widget_to_right(QLabel("Right"))
    widget.show()


def test_logButtons(qtbot, plot_data):
    # Smoke test
    # TODO: could we verify against the log state in the widget? (kind of hard to get that though..)
    widget = LogButtons()
    widget.plot(x=plot_data[0], y=plot_data[1])
    widget.show()
    qtbot.mouseClick(widget.y_log_button, Qt.LeftButton)


@pytest.mark.xfail
def test_offsetPlots(qtbot, plot_data):
    # Smoke test
    widget = OffsetPlots()
    widget.plot(x=plot_data[0], y=plot_data[1])
    widget.show()
    assert False  # TODO: remove once functionality added to OffsetPlots


def test_blend(qtbot, plot_data):
    # Ensure non-BetterLayout and BetterLayout mixins are compatible
    # TODO: upgrade from smoke test (assert that Log button AND curve labels work)
    class BlendClass(CurveLabels, LogButtons): ...
    widget = BlendClass()
    widget.plot(x=plot_data[0], y=plot_data[1])
    widget.show()
    qtbot.wait(5000)