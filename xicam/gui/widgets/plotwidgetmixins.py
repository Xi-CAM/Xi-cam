from functools import wraps
from types import FunctionType

from qtpy.QtWidgets import QApplication, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget, QHBoxLayout, QCheckBox, \
    QSpinBox, QDoubleSpinBox
import pyqtgraph as pg
import numpy as np
from xicam.plugins import live_plugin


# TODO: refactor to support mixin pattern; conflict with plotwidget's attr magic


@live_plugin('PlotMixinPlugin')
class HoverHighlight(pg.PlotWidget):
    """
    Highlights any scatter spots moused-over, giving a feel that they can be clicked on for more info
    """

    def __init__(self, *args, **kwargs):
        super(HoverHighlight, self).__init__(*args, **kwargs)
        self._last_highlighted = None
        self._last_pen = None

    def mouseMoveEvent(self, ev):
        if self._last_highlighted:
            self._last_highlighted.setPen(self._last_pen)
            self._last_highlighted = None

        super(HoverHighlight, self).mouseMoveEvent(ev)

        if self.plotItem.boundingRect().contains(ev.pos()):
            mousePoint = self.plotItem.mapToView(pg.Point(ev.pos()))

            for item in self.scene().items():
                if isinstance(item, pg.PlotDataItem):
                    if item.curve.mouseShape().contains(mousePoint):
                        scatter = item.scatter  # type: pg.ScatterPlotItem
                        points = scatter.pointsAt(mousePoint)
                        if points:
                            self._last_pen = points[0].pen()
                            self._last_highlighted = points[0]
                            points[0].setPen(pg.mkPen("w", width=2))
                            break


@live_plugin('PlotMixinPlugin')
class ClickHighlight(pg.PlotWidget):
    def __init__(self, *args, **kwargs):
        super(ClickHighlight, self).__init__(*args, **kwargs)
        self._last_highlighted = None
        self._last_item = None
        self._last_pen = None
        self._last_curve_pen = None

    def wireup_item(self, item):
        item.sigPointsClicked.connect(self.highlight)
        return item

    def highlight(self, item, points):
        if self._last_item:
            self._last_item.setPen(self._last_curve_pen)
            # self._last_item.setZValue(0)
            self._last_item = None

        self._last_item = item
        self._last_curve_pen = item.opts['pen']
        item.setPen(pg.mkPen('w', width=6))
        # item.setZValue(100)


@live_plugin('PlotMixinPlugin')
class CurveLabels(HoverHighlight, ClickHighlight):
    def __init__(self, *args, **kwargs):
        super(CurveLabels, self).__init__(*args, **kwargs)

        self._arrow = None
        self._text = None
        self._curvepoint = None

    def plot(self, *args, **kwargs):
        if "symbolSize" not in kwargs:
            kwargs["symbolSize"] = 10
        if "symbol" not in kwargs:
            kwargs["symbol"] = "o"
        if "symbolPen" not in kwargs:
            kwargs["symbolPen"] = pg.mkPen((0, 0, 0, 0))
        if "symbolBrush" not in kwargs:
            kwargs["symbolBrush"] = pg.mkBrush((0, 0, 0, 0))

        item = self.plotItem.plot(*args, **kwargs)
        # Note: this is sensitive to order of connections; ClickHighlight seems to regenerate all spots, breaking showLabel unless done in this order
        item.sigPointsClicked.connect(self.showLabel)
        self.wireup_item(item)

        return item

    def showLabel(self, item, points):
        if self._curvepoint:
            self.scene().removeItem(self._arrow)
            self.scene().removeItem(self._text)

        point = points[0]
        self._curvepoint = pg.CurvePoint(item.curve)
        self.addItem(self._curvepoint)
        self._arrow = pg.ArrowItem(angle=90)
        self._arrow.setParentItem(self._curvepoint)
        self._arrow.setZValue(10000)
        self._text = pg.TextItem(f'{item.name()}\nx: {point._data["x"]}\ny: {point._data["y"]}', anchor=(0.5, -.5), border=pg.mkPen("w"), fill=pg.mkBrush("k"))
        self._text.setZValue(10000)
        self._text.setParentItem(self._curvepoint)

        self._curvepoint.setIndex(list(item.scatter.points()).index(point))


class PlotWidget(QWidget):
    """Wrapper for pyqtgraph.PlotWidget that allows mixin extensibility.

    Provides three Qt layouts:
    1. main_layout - vertical box layout that contains the plot view and the bottom widget area
    2. bottom_layout - vertical box layout that contains extra widgets
    3. inner_layout - extra horizontal layout inside the bottom layout

    Use the API provided by pyqtgraph.PlotWidget for plotting.
    """
    def __init__(self, *args, **kwargs):
        super(QWidget, self).__init__(*args, **kwargs)
        self.plot_widget = pg.PlotWidget()

        self.main_layout = QVBoxLayout()
        self.bottom_layout = QVBoxLayout()
        self.inner_layout = QHBoxLayout()

        self.main_layout.addWidget(self.plot_widget)
        self.main_layout.addLayout(self.bottom_layout)
        self.bottom_layout.addLayout(self.inner_layout)

        self.setLayout(self.main_layout)

    # @property
    # def plotItem(self):
    #     return self.plot_widget.plotItem

    def __getattr__(self, attr):
        # implicitly wrap methods from plotItem
        if hasattr(self.plot_widget, attr):
            m = getattr(self.plot_widget, attr)
            if hasattr(m, '__call__'):
                return m
        raise AttributeError(attr)


class OffsetPlots(PlotWidget):
    """Create a visual offset in the plots"""
    # TODO: implement the offset code
    def __init__(self, *args, **kwargs):
        super(OffsetPlots, self).__init__(*args, **kwargs)
        self.offset_box = QDoubleSpinBox()
        self.offset_box.setMinimum(0.0)
        self.offset_box.setDecimals(1)
        self.offset_box.setSingleStep(0.1)
        self.offset_button = QPushButton("Enable Offset")
        self.offset_button.setCheckable(True)
        self.offset_button.toggled.connect(self._offset_toggled)

        layout = QHBoxLayout()
        layout.addWidget(self.offset_box)
        layout.addWidget(self.offset_button)
        self.inner_layout.addLayout(layout)

    def _offset_toggled(self, enabled):
        if enabled:
            self.offset_button.setText("Disable Offset")
        else:
            self.offset_button.setText("Enable Offset")


class XLogButton(PlotWidget):
    """Button mixin that can toggle x-axis log mode."""
    def __init__(self, *args, **kwargs):
        super(XLogButton, self).__init__(*args, **kwargs)
        self.X_ON_TEXT = "X Log Mode On"
        self.X_OFF_TEXT = "X Log Mode Off"

        self.x_log_button = QPushButton(self.X_OFF_TEXT)
        self.x_log_button.setCheckable(True)
        # sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # sizePolicy.setHorizontalStretch(0)
        # sizePolicy.setVerticalStretch(1)
        # sizePolicy.setHeightForWidth(self.x_log_button.sizePolicy().hasHeightForWidth())
        self.x_log_button.toggled.connect(self.set_x_log_mode)
        # Update button check state when pyqtgraph log x checkbox is toggled by user
        self.getPlotItem().ctrl.logXCheck.toggled.connect(self._update_x_button)

        self.inner_layout.addWidget(self.x_log_button)

    def _update_x_button(self, state: bool):
        self.x_log_button.setChecked(state)
        if state:
            self.x_log_button.setText(self.X_ON_TEXT)
        else:
            self.x_log_button.setText(self.X_OFF_TEXT)

    def set_x_log_mode(self, state: bool):
        self._update_x_button(state)
        # Grab existing x log state from pyqtgraph
        y_log_mode = self.getPlotItem().ctrl.logYCheck.isChecked()
        self.setLogMode(x=state, y=y_log_mode)


class YLogButton(PlotWidget):
    """Button mixin that can toggle the y-axis log mode."""
    def __init__(self, *args, **kwargs):
        super(YLogButton, self).__init__(*args, **kwargs)
        self.Y_ON_TEXT = "Y Log Mode On"
        self.Y_OFF_TEXT = "Y Log Mode Off"

        self.y_log_button = QPushButton(self.Y_OFF_TEXT)
        self.y_log_button.setCheckable(True)
        # sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # sizePolicy.setHorizontalStretch(0)
        # sizePolicy.setVerticalStretch(1)
        # sizePolicy.setHeightForWidth(self.y_log_button.sizePolicy().hasHeightForWidth())
        self.y_log_button.toggled.connect(self.set_y_log_mode)
        # Update button check state when pyqtgraph log y checkbox is toggled by user
        self.getPlotItem().ctrl.logYCheck.toggled.connect(self._update_y_button)

        self.inner_layout.addWidget(self.y_log_button)

    def _update_y_button(self, state: bool):
        self.y_log_button.setChecked(state)
        if state:
            self.y_log_button.setText(self.Y_ON_TEXT)
        else:
            self.y_log_button.setText(self.Y_OFF_TEXT)

    def set_y_log_mode(self, state: bool):
        self._update_y_button(state)
        # Grab existing y log state from pyqtgraph
        x_log_mode = self.getPlotItem().ctrl.logXCheck.isChecked()
        self.setLogMode(x=x_log_mode, y=state)


if __name__ == "__main__":
    qapp = QApplication([])

    class ExampleMixinBlend(OffsetPlots, YLogButton, XLogButton, CurveLabels, HoverHighlight):
        ...

    w = ExampleMixinBlend()
    w.plot(x=[1,2,3], y=[2,5,3])
    w.show()

    # w = LogButton()
    # for i in range(1, 10):
    #     pen = pg.mkColor((i, 10))
    #     w.plot(np.arange(1, 101), np.random.random((100,)) + i * 0.5, name=str(i), pen=pen)
    #
    # w.show()

    qapp.exec_()
