from qtpy.QtWidgets import QLayout, QStyle, QSizePolicy, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QScrollArea
from qtpy.QtCore import Qt, QRect, QSize, QPoint, Signal
from pyqtgraph import HistogramLUTWidget, ImageItem, ViewBox, GraphicsLayoutWidget, TextItem


class ActivatableImageItem(ImageItem):
    sigActivated = Signal(object)

    def mouseClickEvent(self, ev):
        super(ActivatableImageItem, self).mouseClickEvent(ev)
        self.sigActivated.emit(self)

    def activate(self):
        self.getViewBox()._viewWidget().setStyleSheet("background-color: gray;")  # TODO: Color the active item differently (not working)

    def deactivate(self):
        self.getViewBox()._viewWidget().setStyleSheet("background-color: black;")


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=-1, hspacing=-1, vspacing=-1):
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
        self.current_image_item = None

        self.setLayout(QHBoxLayout())

        self.scroll_widget = QScrollArea()
        self.scroll_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_widget.setWidgetResizable(True)
        self.flow_widget = QWidget()
        self.flow_layout = FlowLayout()
        self.flow_widget.setLayout(self.flow_layout)
        # self.scroll_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.scroll_widget.setWidget(self.flow_widget)
        self.layout().addWidget(self.scroll_widget)

        self.hist_widget = HistogramLUTWidget()
        self.hist_widget.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        # self.hist_widget.item.setImageItem(self)
        self.hist_widget.item.sigLevelChangeFinished.connect(self.set_levels)
        self.hist_widget.item.sigLookupTableChanged.connect(self.set_lookup_table)
        self.layout().addWidget(self.hist_widget)

        self.first_vb = None
        self.last_vb = None
        self.setStyleSheet("background-color:#000;")

    def set_levels(self, *args, **kwargs):
        levels = self.hist_widget.item.getLevels()
        for image_item in self.image_items:
            image_item.setLevels(levels)

    def set_lookup_table(self, *args, **kwargs):
        lut = self.hist_widget.item.getLookupTable(self.current_image_item.image)
        for image_item in self.image_items:
            image_item.setLookupTable(lut)

    def set_current_imageitem(self, imageitem: ImageItem):
        self.current_image_item.deactivate()
        self.current_image_item = imageitem
        self.current_image_item.activate()
        self.hist_widget.item.setImageItem(self.current_image_item)

    def add_image(self, image, label):
        w = QWidget()
        w.setFixedSize(QSize(500, 500))
        w.setLayout(QVBoxLayout())
        gv = GraphicsLayoutWidget()
        vb = ViewBox(lockAspect=True)
        if self.last_vb:
            vb.setXLink(self.last_vb)
            vb.setYLink(self.last_vb)
        if not self.first_vb:
            self.first_vb = vb
        ii = ActivatableImageItem(image=image)
        ii.sigActivated.connect(self.set_current_imageitem)
        self.hist_widget.item.setImageItem(ii)
        self.current_image_item = ii
        self.image_items.append(ii)
        vb.addItem(ii)
        gv.addItem(vb)

        w.layout().addWidget(gv)
        l = QLabel(label)
        l.setStyleSheet("color: white;")
        w.layout().addWidget(l)

        self.flow_layout.addWidget(w)
        self.last_vb = vb


if __name__ == "__main__":
    from qtpy.QtWidgets import QApplication, QWidget
    import numpy as np

    qapp = QApplication([])

    w = LibraryWidget()
    l = FlowLayout()
    w.setLayout(l)
    last_vb = None

    for i in range(15):
        w.add_image(np.random.random((1000, 1000)), "Test")

    w.show()

    qapp.exec_()

