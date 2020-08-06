from pyqtgraph import ImageView, InfiniteLine, mkPen, ScatterPlotItem, ImageItem, PlotItem, HistogramLUTWidget, \
    GraphicsView
from qtpy.QtGui import QTransform, QPolygonF
from qtpy.QtWidgets import QLabel, QErrorMessage, QSizePolicy, QPushButton, QHBoxLayout, QVBoxLayout, QComboBox, \
    QWidget, QMenu, QAction, QGridLayout
from qtpy.QtCore import Qt, Signal, Slot, QSize, QPointF, QRectF, QObjectCleanupHandler
from xarray import DataArray
import numpy as np
from typing import Tuple, Dict
from xicam.gui.widgets.ROI import BetterCrosshairROI


class NDImageView(QWidget):
    """
    Top-level NDViewer widget

    Internal structure is:

    NDImageView
    - SliceablePanel
    |- SliceableGraphicsView
    |- SliceablePanel
     |- SliceableGraphicsView
     |- SlieablePanel
    ...
    """

    def __init__(self):
        super(NDImageView, self).__init__()
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        self.graphics_view = SliceablePanel(parent=self)

        self.layout().addWidget(self.graphics_view)
        self.layout().addWidget(HistogramLUTWidget())

    def setData(self, data: DataArray):
        self.graphics_view.setData(data, view_dims=data.dims[:2], slc={dim: 0 for dim in data.dims})

    def updateSlicing(self, slice):
        print('newslice:', slice)
        for widget in self.findChildren(SliceablePanel):
            widget.updateSlicing(slice)


class SliceablePanel(QWidget):
    sigSlicingChanged = Signal(object)

    def __init__(self, parent=None):
        super(SliceablePanel, self).__init__(parent=parent)

        assert parent

        self.setLayout(QGridLayout())  # TODO: use splitters
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        self.full_view = SliceableGraphicsView()
        self.right_view = None
        self.top_view = None
        self.corner_view = None
        self.data = None
        self.slice = {}
        self.view_dims = None

        self.layout().addWidget(self.full_view, 1, 0, 1, 1)

        self.full_view.sigToggleHorizontalSlice.connect(self.toggleHorizontalSlice)
        self.full_view.sigToggleVerticalSlice.connect(self.toggleVerticalSlice)

        # Find top-level (NDImageView) widget
        parent = self.parent()
        while not isinstance(parent, NDImageView):
            parent = parent.parent()

        self.sigSlicingChanged.connect(parent.updateSlicing)
        self.full_view.crosshair.sigMoved.connect(self._sliceChangedByCrosshair)

    def _sliceChangedByCrosshair(self):
        view_dims = reversed(self.view_dims)
        slc = {key: value for key, value in zip(view_dims, self.full_view.crosshair.pos())}
        self.sigSlicingChanged.emit(slc)

    @property
    def sliced_data(self):
        slc = {key: value for key, value in self.slice.items() if key not in self.view_dims}
        data = self.data.sel(**slc, method='nearest').transpose(*self.view_dims)
        return data

    def updateSlicing(self, slc):
        self.slice.update(slc)

        self.full_view.setData(self.sliced_data)

        new_crosshair_pos = self.slice[self.view_dims[1]], self.slice[self.view_dims[0]]
        self.full_view.crosshair.setPos(new_crosshair_pos)

    def setData(self, data: DataArray, view_dims: Tuple[str], slc: Dict):
        self.data = data
        self.view_dims = view_dims
        self.slice = slc

        self.full_view.setData(self.sliced_data)

    def toggleHorizontalSlice(self, enable):
        if enable:
            if not self.right_view:
                self.right_view = SliceablePanel(parent=self)
                if self.data is not None:
                    # get the coordinate of the vertical slice
                    # slice = self.full_view.crosshair.pos()[1]

                    # set the right view to the same xarray, but with the second coordinate pre-sliced
                    self.right_view.setData(self.data, view_dims=self.getViewDims('right'), slc=self.slice)
            self.layout().addWidget(self.right_view, 1, 1, 1, 1)
        else:
            self.right_view.hide()

    def toggleVerticalSlice(self, enable):
        if enable:
            if not self.top_view:
                self.top_view = SliceablePanel(parent=self)
                if self.data is not None:
                    # get the coordinate of the horizontal slice
                    # slice = self.full_view.crosshair.pos()[0]

                    # set the top view to the same xarray, but with the first coordinate pre-sliced
                    self.top_view.setData(self.data, view_dims=self.getViewDims('top'), slc=self.slice)
            self.layout().addWidget(self.top_view, 0, 0, 1, 1)
        else:
            self.top_view.hide()

    def getViewDims(self, quadrant: str):
        depth_dim = self.data.dims[max(self.data.dims.index(self.view_dims[1]),self.data.dims.index(self.view_dims[0])) + 1]
        if quadrant == 'right':
            return self.view_dims[0], depth_dim
        elif quadrant == 'top':
            return depth_dim, self.view_dims[1]


class SliceableGraphicsView(GraphicsView):
    sigToggleHorizontalSlice = Signal(bool)
    sigToggleVerticalSlice = Signal(bool)

    def __init__(self):
        super(SliceableGraphicsView, self).__init__()

        self.setContentsMargins(0, 0, 0, 0)

        # Add axes
        self.view = SliceableAxes()
        self.view.axes["left"]["item"].setZValue(10)
        self.view.axes["top"]["item"].setZValue(10)
        self.setCentralItem(self.view)
        self.view.sigToggleVerticalSlice.connect(self.sigToggleVerticalSlice)
        self.view.sigToggleHorizontalSlice.connect(self.sigToggleHorizontalSlice)

        # Add imageitem
        self.image_item = ImageItem()
        self.view.addItem(self.image_item)

        # add crosshair
        self.crosshair = BetterCrosshairROI((0, 0), parent=self.view)
        self.view.addItem(self.crosshair)

    def setData(self, data):

        xvals = data.coords[data.dims[-2]]
        yvals = data.coords[data.dims[-1]]
        xmin = float(xvals.min())
        xmax = float(xvals.max())
        ymin = float(yvals.min())
        ymax = float(yvals.max())

        # Position the image according to coords
        shape = data.shape
        a = [(0, shape[-2]), (shape[-1] - 1, shape[-2]), (shape[-1] - 1, 1), (0, 1)]

        b = [(ymin, xmin), (ymax, xmin), (ymax, xmax), (ymin, xmax)]

        quad1 = QPolygonF()
        quad2 = QPolygonF()
        for p, q in zip(a, b):
            quad1.append(QPointF(*p))
            quad2.append(QPointF(*q))

        transform = QTransform()
        QTransform.quadToQuad(quad1, quad2, transform)

        # Bind coords from the xarray to the timeline axis
        # super(SliceableGraphicsView, self).setImage(img, autoRange, autoLevels, levels, axes, np.asarray(img.coords[img.dims[0]]), pos, scale, transform, autoHistogramRange, levelMode)
        self.image_item.setImage(np.asarray(data))
        self.image_item.setTransform(transform)

        # Label the image axes
        self.view.setLabel('left', data.dims[-2])
        self.view.setLabel('bottom', data.dims[-1])

    def updateImage(self, autoHistogramRange=True):
        ## Redraw image on screen
        if self.image is None:
            return

        image = self.getProcessedImage()

        if autoHistogramRange:
            self.ui.histogram.setHistogramRange(self.levelMin, self.levelMax)

        # Transpose image into order expected by ImageItem
        if self.imageItem.axisOrder == 'col-major':
            axorder = ['t', 'x', 'y', 'c']
        else:
            axorder = ['t', 'y', 'x', 'c']
        axorder = [self.axes[ax] for ax in axorder if self.axes[ax] is not None]
        ax_swap = [image.dims[ax_index] for ax_index in axorder]
        image = image.transpose(*ax_swap)

        # Select time index
        if self.axes['t'] is not None:
            self.ui.roiPlot.show()
            image = image[self.currentIndex]

        self.imageItem.updateImage(np.asarray(image))

    def quickMinMax(self, data):
        """
        Estimate the min/max values of *data* by subsampling. MODIFIED TO USE THE 99TH PERCENTILE instead of max.
        """
        if data is None:
            return 0, 0

        sl = slice(None, None, max(1, int(data.size // 1e6)))
        data = np.asarray(data[sl])

        levels = (np.nanmin(data), np.nanpercentile(np.where(data < np.nanmax(data), data, np.nanmin(data)), 99))

        return [levels]


class SliceableAxes(PlotItem):
    sigToggleHorizontalSlice = Signal(bool)
    sigToggleVerticalSlice = Signal(bool)

    def __init__(self):
        super(SliceableAxes, self).__init__()
        self._menu = None

    def getContextMenus(self, event):
        if self._menu: return None

        menu = QMenu(parent=self.getViewWidget())
        menu.setTitle("Slicing")

        horizontal_action = QAction('Horizontal slice', menu)
        horizontal_action.toggled.connect(self.sigToggleHorizontalSlice)
        horizontal_action.setCheckable(True)
        menu.addAction(horizontal_action)
        vertical_action = QAction('Vertical slice', menu)
        vertical_action.toggled.connect(self.sigToggleVerticalSlice)
        vertical_action.setCheckable(True)
        menu.addAction(vertical_action)

        self._menu = menu

        return menu
