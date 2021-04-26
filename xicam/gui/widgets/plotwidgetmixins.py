from enum import Enum, auto
from functools import wraps
from types import FunctionType
from typing import Union

from qtpy.QtWidgets import QApplication, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget, QHBoxLayout, QCheckBox, \
    QSpinBox, QDoubleSpinBox, QGraphicsProxyWidget, QLayout, QComboBox
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


class BetterLayout(pg.PlotWidget):
    """PlotWidget with a more-easily accessible way to add widgets.

    Provides a few helper methods to add QWidget objects into the PlotWidget.
    You can also add a QLayout (with widgets) into the PlotWidget.
    """
    def __init__(self, *args, **kwargs):
        super(BetterLayout, self).__init__(*args, **kwargs)

    def _create_graphics_item(self, widget: Union[QWidget, QLayout]) -> QGraphicsProxyWidget:
        """Create a graphics item from a standard QWidget (or QLayout),
        which can be added to the PlotWidget's layout.
        """
        if isinstance(widget, QLayout):
            # Wrap passed layout in widget
            # FIXME? Note that adding this widget with layout does not follow the style of the PlotWidget
            container = QWidget()
            # Remove margins (padding around widgets in the layout)
            widget.setContentsMargins(0, 0, 0, 0)
            container.setLayout(widget)
            widget = container
        return self.sceneObj.addWidget(widget)

    def layout(self):
        """Return the graphics layout used in the PlotWidget (QGraphicsGridLayout)."""
        # For some reason, using self.centralLayout gives C++ wrapper deleted error
        return self.centralWidget.layout

    def add_widget_to_bottom(self, widget: QWidget):
        """Add a QWidget to the bottom of the PlotWidget."""
        graphics_widget = self._create_graphics_item(widget)
        self.layout().addItem(graphics_widget, self.layout().rowCount(), 1)

    def add_widget_to_right(self, widget: QWidget):
        """Add add QWidget to the right of the PlotWidget."""
        graphics_widget = self._create_graphics_item(widget)
        self.layout().addItem(graphics_widget, 0, self.layout().columnCount())


class OffsetPlots(BetterLayout):
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
        self.add_widget_to_bottom(layout)

    def _offset_toggled(self, enabled):
        if enabled:
            self.offset_button.setText("Disable Offset")
        else:
            self.offset_button.setText("Enable Offset")


class LogButtons(BetterLayout):
    """Button mixin that can toggle x/y log modes."""
    def __init__(self, *args, **kwargs):
        super(LogButtons, self).__init__(*args, **kwargs)
        # Define single-source of text state
        self.X_ON_TEXT = "X Log Mode On"
        self.X_OFF_TEXT = "X Log Mode Off"
        self.Y_ON_TEXT = "Y Log Mode On"
        self.Y_OFF_TEXT = "Y Log Mode Off"

        # Create checkable buttons
        self.x_log_button = QPushButton(self.X_OFF_TEXT)
        self.x_log_button.setCheckable(True)
        self.x_log_button.toggled.connect(self.set_x_log_mode)
        self.y_log_button = QPushButton(self.Y_OFF_TEXT)
        self.y_log_button.setCheckable(True)
        self.y_log_button.toggled.connect(self.set_y_log_mode)

        # Update button check state when pyqtgraph log x checkbox is toggled by user
        self.getPlotItem().ctrl.logXCheck.toggled.connect(self._update_x_button)
        # Update button check state when pyqtgraph log y checkbox is toggled by user
        self.getPlotItem().ctrl.logYCheck.toggled.connect(self._update_y_button)

        # Create a layout to have these buttons side-by-side
        layout = QHBoxLayout()
        layout.addWidget(self.x_log_button)
        layout.addWidget(self.y_log_button)
        # TODO: BetterLayout
        #  RightLayout   BottomLayout
        #  add_widget    add_widget
        self.add_widget_to_bottom(layout)

    def _update_y_button(self, state: bool):
        self.y_log_button.setChecked(state)
        if state:
            self.y_log_button.setText(self.Y_ON_TEXT)
        else:
            self.y_log_button.setText(self.Y_OFF_TEXT)

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

    def set_y_log_mode(self, state: bool):
        self._update_y_button(state)
        # Grab existing y log state from pyqtgraph
        x_log_mode = self.getPlotItem().ctrl.logXCheck.isChecked()
        self.setLogMode(x=x_log_mode, y=state)


# @live_plugin('PlotMixinPlugin')
class ToggleSymbols(BetterLayout):
    """Simple mixin that adds a button to toggle 'o' symbols on plot data curves in the plot widget."""
    def __init__(self, *args, **kwargs):
        super(ToggleSymbols, self).__init__(*args, **kwargs)

        self.toggle_symbols_button = QPushButton("Toggle Symbols")
        self.toggle_symbols_button.setCheckable(True)
        self.add_widget_to_right(self.toggle_symbols_button)

        self.toggle_symbols_button.toggled.connect(self._toggle_symbol)

        self._symbol_cache = []

    def _toggle_symbol(self, checked: bool):
        for item in self.scene().items():
            if isinstance(item, pg.PlotDataItem):
                if checked:
                    item.setData(symbol=None)
                else:
                    item.setData(symbol='o')


if __name__ == "__main__":
    qapp = QApplication([])

    class LabelMixin(BetterLayout):
        """Example mixin using BetterLayout.

        Adds a label to the bottom of the plot widget, and a button to the right side.
        """
        def __init__(self, *args, **kwargs):
            super(LabelMixin, self).__init__(*args, **kwargs)
            label = QLabel("Bottom Label")
            btn = QPushButton("Right Button")
            self.add_widget_to_bottom(label)
            self.add_widget_to_right(btn)


    class ExampleMixinBlend(LabelMixin, CurveLabels, OffsetPlots, LogButtons):
        """Example mixin blend using a BetterLayout-based mixin and a directly derived PlotWidget mixin.

        Note order of BetterLayout mixins matters: mixins are processed right-to-left.
        So, LogButtons will be on the top of the custom layout section in the PlotWidget.
        """
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
