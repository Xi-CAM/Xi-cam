"""
This patch module adds color gradients like matplotlib's viridis etc. to PyQtGraph
"""
import numpy as np
from pyqtgraph.graphicsItems import GradientEditorItem
from collections import OrderedDict
from qtpy.QtWidgets import QTreeWidgetItem, QWidget, QPushButton, QCheckBox
from qtpy.QtGui import QIcon, QPainterPath
from qtpy.QtCore import Signal
from xicam.core import msg
from xicam.gui.static import path

from pyqtgraph.parametertree.parameterTypes import WidgetParameterItem, ListParameter
import pyqtgraph as pg

GradientEditorItem.__dict__["Gradients"] = OrderedDict(
    [
        (
            "thermal",
            {
                "ticks": [
                    (0.3333, (185, 0, 0, 255)),
                    (0.6666, (255, 220, 0, 255)),
                    (1, (255, 255, 255, 255)),
                    (0, (0, 0, 0, 255)),
                ],
                "mode": "rgb",
            },
        ),
        (
            "flame",
            {
                "ticks": [
                    (0.2, (7, 0, 220, 255)),
                    (0.5, (236, 0, 134, 255)),
                    (0.8, (246, 246, 0, 255)),
                    (1.0, (255, 255, 255, 255)),
                    (0.0, (0, 0, 0, 255)),
                ],
                "mode": "rgb",
            },
        ),
        (
            "yellowy",
            {
                "ticks": [
                    (0.0, (0, 0, 0, 255)),
                    (0.2328863796753704, (32, 0, 129, 255)),
                    (0.8362738179251941, (255, 255, 0, 255)),
                    (0.5257586450247, (115, 15, 255, 255)),
                    (1.0, (255, 255, 255, 255)),
                ],
                "mode": "rgb",
            },
        ),
        (
            "bipolar",
            {
                "ticks": [
                    (0.0, (0, 255, 255, 255)),
                    (1.0, (255, 255, 0, 255)),
                    (0.5, (0, 0, 0, 255)),
                    (0.25, (0, 0, 255, 255)),
                    (0.75, (255, 0, 0, 255)),
                ],
                "mode": "rgb",
            },
        ),
        (
            "viridis",
            {
                "ticks": [
                    (0.0, (68, 1, 84, 255)),
                    (0.25, (58, 82, 139, 255)),
                    (0.5, (32, 144, 140, 255)),
                    (0.75, (94, 201, 97, 255)),
                    (1.0, (253, 231, 36, 255)),
                ],
                "mode": "rgb",
            },
        ),
        (
            "inferno",
            {
                "ticks": [
                    (0.0, (0, 0, 3, 255)),
                    (0.25, (87, 15, 109, 255)),
                    (0.5, (187, 55, 84, 255)),
                    (0.75, (249, 142, 8, 255)),
                    (1.0, (252, 254, 164, 255)),
                ],
                "mode": "rgb",
            },
        ),
        (
            "plasma",
            {
                "ticks": [
                    (0.0, (12, 7, 134, 255)),
                    (0.25, (126, 3, 167, 255)),
                    (0.5, (203, 71, 119, 255)),
                    (0.75, (248, 149, 64, 255)),
                    (1.0, (239, 248, 33, 255)),
                ],
                "mode": "rgb",
            },
        ),
        (
            "magma",
            {
                "ticks": [
                    (0.0, (0, 0, 3, 255)),
                    (0.25, (80, 18, 123, 255)),
                    (0.5, (182, 54, 121, 255)),
                    (0.75, (251, 136, 97, 255)),
                    (1.0, (251, 252, 191, 255)),
                ],
                "mode": "rgb",
            },
        ),
        ("spectrum", {"ticks": [(1.0, (255, 0, 255, 255)), (0.0, (255, 0, 0, 255))], "mode": "hsv"}),
        ("cyclic", {"ticks": [(0.0, (255, 0, 4, 255)), (1.0, (255, 0, 0, 255))], "mode": "hsv"}),
        (
            "greyclip",
            {"ticks": [(0.0, (0, 0, 0, 255)), (0.99, (255, 255, 255, 255)), (1.0, (255, 0, 0, 255))], "mode": "rgb"},
        ),
        ("grey", {"ticks": [(0.0, (0, 0, 0, 255)), (1.0, (255, 255, 255, 255))], "mode": "rgb"}),
    ]
)

from pyqtgraph.parametertree import Parameter, ParameterItem, registerParameterType
from pyqtgraph.parametertree import parameterTypes
from pyqtgraph.widgets.SpinBox import SpinBox
from pyqtgraph.widgets.ColorButton import ColorButton
from pyqtgraph import ImageView, ROI, PolyLineROI, ErrorBarItem
import numpy as np
from qtpy.QtCore import QSize
from qtpy.QtGui import QBrush, QPalette
import pyqtgraph


class ImageView(ImageView):
    def timeIndex(self, slider):
        ## Return the time and frame index indicated by a slider
        if self.image is None:
            return (0, 0)

        t = slider.value()

        if not hasattr(self, "tVals"):
            return (0, 0)

        xv = self.tVals
        if xv is None:
            ind = int(t)
        else:
            if len(xv) < 2:
                return (0, 0)
            inds = np.argwhere(xv <= t)  # <- The = is import to reach the last value
            if len(inds) < 1:
                return (0, t)
            ind = inds[-1, 0]
        return ind, t

    def setCurrentIndex(self, ind):
        super(ImageView, self).setCurrentIndex(ind)
        (ind, time) = self.timeIndex(self.timeLine)
        self.sigTimeChanged.emit(ind, time)


pyqtgraph.__dict__["ImageView"] = ImageView


class PolyLineROI(PolyLineROI):
    def getArrayRegion(self, data, img, axes=(0, 1), **kwds):
        """
        Return the result of ROI.getArrayRegion(), masked by the shape of the
        ROI. Values outside the ROI shape are set to 0.
        """
        br = self.boundingRect()
        if br.width() > 1000:
            raise Exception()
        sliced = ROI.getArrayRegion(self, data, img, axes=axes, fromBoundingRect=True, **kwds)
        if kwds.get("returnMappedCoords"):
            sliced, mapped = sliced

        if img.axisOrder == "col-major":
            mask = self.renderShapeMask(sliced.shape[axes[0]], sliced.shape[axes[1]])
        else:
            mask = self.renderShapeMask(sliced.shape[axes[1]], sliced.shape[axes[0]])
            mask = mask.T

        # reshape mask to ensure it is applied to the correct data axes
        shape = [1] * data.ndim
        shape[axes[0]] = sliced.shape[axes[0]]
        shape[axes[1]] = sliced.shape[axes[1]]
        mask = mask.reshape(shape)

        if kwds.get("returnMappedCoords"):
            return sliced * mask, mapped
        else:
            return sliced * mask


pyqtgraph.__dict__["PolyLineROI"] = PolyLineROI


class SafeImageView(ImageView):
    def setImage(self, img, *args, **kwargs):
        if len(getattr(img, "shape", [])) < 2:
            return
        if len(img) < 4:
            return
        super(SafeImageView, self).setImage(np.squeeze(img), *args, **kwargs)


class ImageParameterItem(WidgetParameterItem):
    def makeWidget(self):
        self.subItem = QTreeWidgetItem()
        self.addChild(self.subItem)

        w = SafeImageView()
        w.value = lambda: w.image
        w.setValue = w.setImage
        w.sigChanged = None
        # Shrink LUT
        w.getHistogramWidget().setMinimumWidth(5)
        w.ui.menuBtn.setParent(None)
        w.ui.roiBtn.setParent(None)

        self.hideWidget = False
        return w

    def treeWidgetChanged(self):
        ## TODO: fix so that superclass method can be called
        ## (WidgetParameter should just natively support this style)
        # WidgetParameterItem.treeWidgetChanged(self)
        if self.treeWidget():
            self.treeWidget().setFirstItemColumnSpanned(self.subItem, True)
            self.treeWidget().setItemWidget(self.subItem, 0, self.widget)

        # for now, these are copied from ParameterItem.treeWidgetChanged
        self.setHidden(not self.param.opts.get("visible", True))
        self.setExpanded(self.param.opts.get("expanded", True))

    def valueChanged(self, param, val, force=False):
        ## called when the parameter's value has changed
        ParameterItem.valueChanged(self, param, val)
        if force or not np.array_equal(val, self.widget.value()):
            self.widget.setValue(val)
        self.updateDisplayLabel(val)  ## always make sure label is updated, even if values match!

    def updateDefaultBtn(self):
        pass


class ImageParameter(Parameter):
    itemClass = ImageParameterItem

    def __init__(self, *args, **kwargs):
        if "expanded" not in kwargs:
            kwargs["expanded"] = False
        super(ImageParameter, self).__init__(*args, **kwargs)

    def setValue(self, value, blockSignal=None):
        """
        Set the value of this Parameter; return the actual value that was set.
        (this may be different from the value that was requested)
        """
        try:
            if blockSignal is not None:
                self.sigValueChanged.disconnect(blockSignal)
            if np.array_equal(self.opts["value"], value):
                return value
            self.opts["value"] = value
            # self.sigValueChanged.emit(self, value)
        finally:
            if blockSignal is not None:
                self.sigValueChanged.connect(blockSignal)

        return value

    def setDefault(self, val):
        """Set the default value for this parameter."""
        if np.all(self.opts['default'] == val):
            return
        self.opts['default'] = val
        self.sigDefaultChanged.emit(self, val)


registerParameterType("ndarray", ImageParameter, override=True)


class FixableWidgetParameterItem(parameterTypes.WidgetParameterItem):
    def __init__(self, param, depth):
        super(FixableWidgetParameterItem, self).__init__(param, depth)
        if param.opts.get("fixable"):
            self.fixbutton = QPushButton()
            self.fixbutton.setFixedWidth(20)
            self.fixbutton.setFixedHeight(20)
            self.fixbutton.setCheckable(True)
            self.fixbutton.setChecked(param.opts["fixed"])
            self.fixbutton.toggled.connect(param.sigFixToggled)
            self.fixbutton.toggled.connect(lambda fixed: param.setOpts(fixed=fixed))
            # self.fixbutton.toggled.connect(lambda fixed: self.widgetValueChanged())

            self.fixbutton.setIcon(QIcon(path("icons/anchor.png")))
            self.layoutWidget.layout().addWidget(self.fixbutton)

    def optsChanged(self, param, opts):
        """Called when any options are changed that are not
        name, value, default, or limits"""
        # print "opts changed:", opts
        ParameterItem.optsChanged(self, param, opts)

        if "readonly" in opts:
            self.updateDefaultBtn()
            if isinstance(self.widget, (QCheckBox, ColorButton)):
                self.widget.setEnabled(not opts["readonly"])

        ## If widget is a SpinBox, pass options straight through
        if isinstance(self.widget, SpinBox):
            if "units" in opts and "suffix" not in opts:
                opts["suffix"] = opts["units"]
            try:  # patch passes silently for 'fixed'
                self.widget.setOpts(**opts)
            except TypeError:
                pass
            self.updateDisplayLabel()


class FixableSimpleParameter(parameterTypes.SimpleParameter):
    itemClass = FixableWidgetParameterItem
    sigFixToggled = Signal(bool)


registerParameterType("int", FixableSimpleParameter, override=True)
registerParameterType("float", FixableSimpleParameter, override=True)


class BetterGroupParameteritem(parameterTypes.GroupParameterItem):
    def updateDepth(self, depth):

        ## Change item's appearance based on its depth in the tree
        ## This allows highest-level groups to be displayed more prominently.
        if depth == 0:
            for c in [0, 1]:
                self.setBackground(c, QBrush(QPalette().color(QPalette.Light)))
                # self.setForeground(c, QBrush(QPalette().color(QPalette.Dark)))
                font = self.font(c)
                font.setBold(True)
                font.setPointSize(font.pointSize() + 1)
                self.setFont(c, font)
                self.setSizeHint(0, QSize(0, 25))
        else:
            for c in [0, 1]:
                self.setBackground(c, QBrush(QPalette().color(QPalette.Light)))
                font = self.font(c)
                font.setBold(True)
                # font.setPointSize(font.pointSize()+1)
                self.setFont(c, font)
                self.setSizeHint(0, QSize(0, 20))


class BetterGroupParameter(parameterTypes.GroupParameter):
    itemClass = BetterGroupParameteritem


parameterTypes.GroupParameter = BetterGroupParameter
registerParameterType("group", BetterGroupParameter, override=True)


class TupleGroupParameter(BetterGroupParameter):
    """Parameter for tuples in the ParameterTree.

    A tuple will be represented as a group parameter,
    where each child will be the tuple's name with an integer subscript appended to it.

    For example, for a tuple named "x" with values (1, 3, 9), we will get a parameter tree that looks like:
    x
       x₀    1
       x₁    3
       x₂    9
    """
    itemClass = BetterGroupParameteritem

    def __init__(self, **opts):
        super(TupleGroupParameter, self).__init__(**opts)

        name = opts.get('name')
        # Add spacing for non single-character names
        if len(name) > 1:
            name += " "
        values = opts.get('value')
        defaults = opts.get('default')

        # Map an integer to its corresponding unicode subscript literal
        def subscript(n: int):
            subscripts = "\u2080\u2081\u2082\u2083\u2084\u2085\u2086\u2087\u2088\u2089"
            return "".join([subscripts[ord(c) - ord('0')] for c in str(n)])

        # Create child param dicts (so Parameter.create is used in addChild)
        # where each element in the tuple is marked with a subscript of its index position
        # e.g. gains = (1, 4, 8) -> gains 0, gains 1, gains 2 (note that the numbers are subscript when shown)
        if values is None:
            if defaults is None:
                # FIXME: better exception
                message = f"TupleGroupParameter named \"{name}\" must have default values provided"
                msg.notifyMessage(message, level=msg.ERROR)
                raise Exception(message)
            else:
                values = defaults

        for i in range(len(values)):
            value = values[i]
            default_value = defaults[i]
            param_type = type(values[i]).__name__
            child_name = f"{name}{subscript(i)}"
            child = {"name": child_name, "type": param_type, "default": default_value, "value": value}
            self.addChild(child)


registerParameterType("tuple", TupleGroupParameter, override=True)


class CounterGroupParameterItem(BetterGroupParameteritem):
    def __init__(self, *args, **kwargs):
        super(CounterGroupParameterItem, self).__init__(*args, **kwargs)
        self.param.sigChildAdded.connect(self.updateText)
        self.param.sigChildRemoved.connect(self.updateText)

    def updateText(self, *_):
        self.setText(0, f"{self.param.name()} ({self.childCount()})")


class CounterGroupParameter(BetterGroupParameter):
    itemClass = CounterGroupParameterItem


registerParameterType("countergroup", CounterGroupParameter, override=True)


class LazyGroupParameterItem(BetterGroupParameteritem):
    # Note: no accounting for if items are removed

    def __init__(self, *args, **kwargs):
        super(LazyGroupParameterItem, self).__init__(*args, **kwargs)
        self._queuedchildren = []

    @staticmethod
    def initialize_treewidget(treewidget):
        treewidget.itemExpanded.connect(LazyGroupParameterItem.itemExpanded)

    @staticmethod
    def itemExpanded(item):
        for i in range(item.childCount()):
            if hasattr(item.child(i), "flushChildren"):
                item.child(i).flushChildren()

    def childAdded(self, *childargs):
        self._queuedchildren.append(childargs)
        if self.isExpanded():
            self.flushChildren()

    def flushChildren(self):
        while len(self._queuedchildren):
            super(LazyGroupParameterItem, self).childAdded(*self._queuedchildren.pop())


class LazyGroupParameter(BetterGroupParameter):
    itemClass = LazyGroupParameterItem


registerParameterType("lazygroup", LazyGroupParameter, override=True)


class EnumListParameter(ListParameter):
    def __init__(self, **opts):
        super(EnumListParameter, self).__init__(**opts)
        self.setLimits(opts['limits'])


registerParameterType('EnumMeta', EnumListParameter, override=True)


class LogCompatibleErrorBarItem(ErrorBarItem):
    def __init__(self, **opts):
        super(LogCompatibleErrorBarItem, self).__init__(**opts)
        self.opts['xlog'] = False
        self.opts['ylog'] = False

    def setLogMode(self, x:bool=None, y:bool=None):
        if x is not None and x!=self.opts['xlog']:
            self.setData(xlog=x)
        if y is not None and y!=self.opts['ylog']:
            self.setData(ylog=y)

    def drawPath(self):
        p = QPainterPath()

        x, y = self.opts['x'], self.opts['y']
        if x is None or y is None:
            self.path = p
            return

        if self.opts['xlog']:
            x = np.log10(x)
        if self.opts['ylog']:
            y = np.log10(y)

        beam = self.opts['beam']

        height, top, bottom = self.opts['height'], self.opts['top'], self.opts['bottom']
        if height is not None or top is not None or bottom is not None:
            ## draw vertical error bars
            if height is not None:
                y1 = y - height / 2.
                y2 = y + height / 2.
            else:
                if bottom is None:
                    y1 = y
                else:
                    y1 = y - bottom
                if top is None:
                    y2 = y
                else:
                    y2 = y + top

            for i in range(len(x)):
                p.moveTo(x[i], y1[i])
                p.lineTo(x[i], y2[i])

            if beam is not None and beam > 0:
                x1 = x - beam / 2.
                x2 = x + beam / 2.
                if height is not None or top is not None:
                    for i in range(len(x)):
                        p.moveTo(x1[i], y2[i])
                        p.lineTo(x2[i], y2[i])
                if height is not None or bottom is not None:
                    for i in range(len(x)):
                        p.moveTo(x1[i], y1[i])
                        p.lineTo(x2[i], y1[i])

        width, right, left = self.opts['width'], self.opts['right'], self.opts['left']
        if width is not None or right is not None or left is not None:
            ## draw vertical error bars
            if width is not None:
                x1 = x - width / 2.
                x2 = x + width / 2.
            else:
                if left is None:
                    x1 = x
                else:
                    x1 = x - left
                if right is None:
                    x2 = x
                else:
                    x2 = x + right

            for i in range(len(x)):
                p.moveTo(x1[i], y[i])
                p.lineTo(x2[i], y[i])

            if beam is not None and beam > 0:
                y1 = y - beam / 2.
                y2 = y + beam / 2.
                if width is not None or right is not None:
                    for i in range(len(x)):
                        p.moveTo(x2[i], y1[i])
                        p.lineTo(x2[i], y2[i])
                if width is not None or left is not None:
                    for i in range(len(x)):
                        p.moveTo(x1[i], y1[i])
                        p.lineTo(x1[i], y2[i])

        self.path = p
        self.prepareGeometryChange()


pg.ErrorBarItem = LogCompatibleErrorBarItem
