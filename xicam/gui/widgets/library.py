import numpy as np
from xarray.core.dataarray import DataArray
from qtpy.QtWidgets import QLayout, QStyle, QSizePolicy, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QScrollArea, QFrame, QAbstractItemView, QScrollBar, QPushButton, QGraphicsView
from qtpy.QtCore import Qt, QRect, QSize, QPoint, Signal, QModelIndex, QRectF, QPointF, QSignalBlocker
from qtpy.QtGui import QWheelEvent
from pyqtgraph import HistogramLUTWidget, ImageItem, ViewBox, GraphicsLayoutWidget, TextItem
from xicam.core.data.bluesky_utils import guess_stream_field, preview


def normalize_labels(da: DataArray):
    # ...infer what axis the "time" axis actually is
    da = da.rename({"time": "E"})

    # ...reshape flattened axes
    ...

    # ...replace the "time" axis' coords with more meaningful thing
    da = da.assign_coords({"E": range(da.shape[0])})

    return da


class ScrollableGraphicsLayoutWidget(GraphicsLayoutWidget):
    def wheelEvent(self, ev: QWheelEvent):
        # GraphicsLayoutWidget forcibly ignores if an event was accepted, and changes its state to ignored.
        # This causes parents to have no knowledge of if its children accepted the event or not.
        # To prevent that behavior, we only process the event if it wasn't accepted.
        if not ev.isAccepted():
            QGraphicsView.wheelEvent(self, ev)


class ActivatableImageItem(ImageItem):
    # TODO: Give 'active' item special styling
    sigActivated = Signal(object)

    def mouseClickEvent(self, ev):
        super(ActivatableImageItem, self).mouseClickEvent(ev)
        self.sigActivated.emit(self)

    def activate(self):
        pass
        # self.getViewBox()._viewWidget().setStyleSheet("background-color: gray;")  # TODO: Color the active item differently (not working)

    def deactivate(self):
        pass
        # self.getViewBox()._viewWidget().setStyleSheet("background-color: black;")


class FlowLayout(QLayout):
    """
    This layout is like a QGridLayout, but it automatically adjusts its number of columns to fit its parent, wrapping
    items to the next line. Adapted from https://gist.github.com/Cysu/7461066
    """
    def __init__(self, parent=None, margin: int =-1, hspacing: int =-1, vspacing: int=-1):
        super(FlowLayout, self).__init__(parent)
        self._hspacing = hspacing
        self._vspacing = vspacing
        self._items = []
        self.setContentsMargins(margin, margin, margin, margin)

    def __del__(self):
        del self._items[:]

    def addItem(self, item):
        self._items.append(item)

    def horizontalSpacing(self):
        if self._hspacing >= 0:
            return self._hspacing
        else:
            return self.smartSpacing(
                QStyle.PM_LayoutHorizontalSpacing)

    def verticalSpacing(self):
        if self._vspacing >= 0:
            return self._vspacing
        else:
            return self.smartSpacing(
                QStyle.PM_LayoutVerticalSpacing)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)

    def expandingDirections(self):
        return Qt.Orientations(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect:QRect):
        super(FlowLayout, self).setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        left, top, right, bottom = self.getContentsMargins()
        size += QSize(left + right, top + bottom)
        return size

    def doLayout(self, rect, testonly):
        left, top, right, bottom = self.getContentsMargins()
        effective = rect.adjusted(+left, +top, -right, -bottom)
        x = effective.x()
        y = effective.y()
        lineheight = 0
        for item in self._items:
            widget = item.widget()
            hspace = self.horizontalSpacing()
            if hspace == -1:
                hspace = widget.style().layoutSpacing(
                    QSizePolicy.PushButton,
                    QSizePolicy.PushButton, Qt.Horizontal)
            vspace = self.verticalSpacing()
            if vspace == -1:
                vspace = widget.style().layoutSpacing(
                    QSizePolicy.PushButton,
                    QSizePolicy.PushButton, Qt.Vertical)
            nextX = x + item.sizeHint().width() + hspace
            if nextX - hspace > effective.right() and lineheight > 0:
                x = effective.x()
                y = y + lineheight + vspace
                nextX = x + item.sizeHint().width() + hspace
                lineheight = 0
            if not testonly:
                item.setGeometry(
                    QRect(QPoint(x, y), item.sizeHint()))
            x = nextX
            lineheight = max(lineheight, item.sizeHint().height())
        return y + lineheight - rect.y() + bottom

    def smartSpacing(self, pm):
        parent = self.parent()
        if parent is None:
            return -1
        elif parent.isWidgetType():
            return parent.style().pixelMetric(pm, None, parent)
        else:
            return parent.spacing()


class LibraryWidget(QWidget):
    sigImageChanged = Signal()

    def __init__(self):
        super(LibraryWidget, self).__init__()
        self.image_items = []
        self.views = []
        self.current_image_item = None

        self.setLayout(QHBoxLayout())
        self.right_layout = QVBoxLayout()

        self.scroll_widget = QScrollArea()
        self.scroll_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_widget.setWidgetResizable(True)
        self.flow_widget = QWidget()
        self.flow_layout = FlowLayout()
        self.flow_widget.setLayout(self.flow_layout)
        self.scroll_widget.setWidget(self.flow_widget)
        self.layout().addWidget(self.scroll_widget)

        self.hist_widget = HistogramLUTWidget()
        self.hist_widget.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.hist_widget.item.sigLevelChangeFinished.connect(self.set_levels)
        self.hist_widget.item.sigLookupTableChanged.connect(self.set_lookup_table)
        self.layout().addLayout(self.right_layout)
        self.right_layout.addWidget(self.hist_widget)

        self.link_button = QPushButton("Link Axes")
        self.link_button.setCheckable(True)
        self.right_layout.addWidget(self.link_button)

        # TODO: use Qt styling pallet for theming
        # self.setStyleSheet("background-color:#000;")

        self.current_view = None
        self.axes_linked = False

    def set_slice(self, *args, **kwargs):
        # TODO: support generic orthogonal slicing
        print('slice:', args, kwargs)

    def set_levels(self, *args, **kwargs):
        levels = self.hist_widget.item.getLevels()
        for image_item in self.image_items:
            image_item.setLevels(levels)

    def set_lookup_table(self, *args, **kwargs):
        if self.current_image_item and self.current_image_item.image is not None:
            lut = self.hist_widget.item.getLookupTable(self.current_image_item.image)
            for image_item in self.image_items:
                image_item.setLookupTable(lut)

    def set_current_imageitem(self, imageitem: ImageItem):
        if self.current_image_item:
            self.current_image_item.deactivate()
        self.current_image_item = imageitem
        self.current_view = imageitem.getViewBox()
        self.current_image_item.activate()
        self.hist_widget.item.setImageItem(self.current_image_item)

    def propagate_axes(self):
        if self.link_button.isChecked():
            view = self.sender()
            view_rect = view.viewRect()

            for other_view in self.views:
                if other_view is not view:
                    with QSignalBlocker(other_view):
                        other_view.setRange(rect=view_rect, padding=0)

    def add_image(self, image, label):
        w = QFrame()
        w.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        w.setLineWidth(2)
        w.setFixedSize(QSize(500, 500))
        w.setLayout(QVBoxLayout())
        gv = ScrollableGraphicsLayoutWidget()
        vb = ViewBox(lockAspect=True)
        ii = ActivatableImageItem(image=image)
        ii.sigActivated.connect(self.set_current_imageitem)
        self.hist_widget.item.setImageItem(ii)
        self.current_image_item = ii
        self.image_items.append(ii)
        self.views.append(vb)
        vb.sigRangeChangedManually.connect(self.propagate_axes)
        vb.addItem(ii)
        gv.addItem(vb)
        self.set_current_imageitem(ii)

        w.layout().addWidget(gv)
        l = QLabel(label)
        # l.setStyleSheet("color: white;")
        w.layout().addWidget(l)

        self.flow_layout.addWidget(w)
        self.last_vb = vb

    def update_image(self, index, image, label):
        if index < len(self.image_items):
            self.image_items[index].setImage(image)
        else:
            self.add_image(image, label)


class LibraryView(QAbstractItemView):
    def __init__(self, model=None, parent=None, slice:dict =None):
        super(LibraryView, self).__init__(parent)
        self._libraryWidget = LibraryWidget()
        self._libraryWidget.setParent(self)
        self.scrollbar = self._libraryWidget.scroll_widget.verticalScrollBar()  # type: QScrollBar
        self.scrollbar.valueChanged.connect(self.checkViewport)
        ###########self._indexToTabMap = OrderedDict()

        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self._libraryWidget)

        self.slice = slice or {}

        if model:
            self.setModel(model)

            # initialize with all of the model's cache
            self.dataChanged(self.model().createIndex(0,0),
                             self.model().createIndex(self.model().rowCount(QModelIndex()) + 1, 0))

            # check if more runs need to be cached to fill the viewport
            self.checkViewport()

    def checkViewport(self):
        # if the scrollbar is near its max
        while self.scrollbar.value() == self.scrollbar.maximum() and self.model().canFetchMore(QModelIndex()):
            # Fetch more items from the model
            self.model().fetchMore(QModelIndex())

    def dataChanged(self, topLeft: QModelIndex, bottomRight: QModelIndex, roles=None):
        """
        Re-implements the QAbstractItemView.dataChanged() slot.

        When the data attached to the Qt.CheckStateRole has been changed, this will either render a Hint or remove the
        Hint visualization.

        Parameters
        ----------
        topLeft
            For now, the only index we are concerned with, which corresponds to the item's check state changing.
        bottomRight
            (Unused right now)
        roles
            List of roles attached to the data state change.

        """
        if roles is None:
            roles = []
        if self.model():
            # empty list indicates ALL roles have changed (see documentation)
            for row in range(topLeft.row(), bottomRight.row()):
                if row >= self.model().rowCount(QModelIndex()) and self.model().canFetchMore(QModelIndex()):  # ensure that the item we retrieve is always cached
                    self.model().fetchMore(QModelIndex())

                catalog = self.model()._cache[row]
                if catalog:
                    stream, field = guess_stream_field(catalog)
                    data = np.squeeze(np.asarray(normalize_labels(getattr(catalog, stream).to_dask()[field])[self.slice].compute()))

                    self._libraryWidget.update_image(row, data, f"({catalog.name})[{stream}]<{field}>")

        super(LibraryView, self).dataChanged(topLeft, bottomRight, roles)

    def horizontalOffset(self):
        return 0

    def indexAt(self, point: QPoint):
        return QModelIndex()

    def moveCursor(self, QAbstractItemView_CursorAction, Union, Qt_KeyboardModifiers=None, Qt_KeyboardModifier=None):
        return QModelIndex()

    def rowsInserted(self, index: QModelIndex, start, end):
        return

    def rowsAboutToBeRemoved(self, index: QModelIndex, start, end):
        return

    def scrollTo(self, QModelIndex, hint=None):
        return

    def verticalOffset(self):
        return 0

    def visualRect(self, QModelIndex):
        from qtpy.QtCore import QRect
        return QRect()

    def set_slice(self, value, axis):
        self.slice[axis] = value
        self.dataChanged(self.model().createIndex(0,0),
                         self.model().createIndex(self.model().rowCount(QModelIndex()),0))