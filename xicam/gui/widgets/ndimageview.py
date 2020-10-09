from functools import partial
from itertools import zip_longest
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
from xicam.core import threads

# TODO: block efficient subsampling


class NDImageView(QWidget):
    sigImageChanged = Signal()
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

        self.lut = None
        self.levels = None
        self.data = None
        self.histogram_subsampling_axes = None
        self.histogram_max_sample_size = 1e6

        self.graphics_view = SliceablePanel(parent=self)
        self.lut_widget = HistogramLUTWidget(parent=self)
        self.lut_widget.item.setImageItem(self)

        self.graphics_view.sigMakePrimary.connect(self.setPrimary)

        self.layout().addWidget(self.graphics_view)
        self.layout().addWidget(self.lut_widget)

        self.setStyleSheet('NDImageView {background-color:black;}')

    def setData(self, data: DataArray, view_dims=None, slc=None, reset_crosshairs=True):
        self.data = data

        full_slc = {dim: 0 for dim in data.dims}
        if slc:
            full_slc.update(slc)

        if view_dims:
            new_dims = [dim for dim in dict(zip_longest(view_dims+data.dims, [None])).keys()]
            data = data.transpose(*new_dims)
        else:
            view_dims = data.dims[:2]

        self.graphics_view.setData(data, view_dims=view_dims, slc=full_slc)

        if reset_crosshairs:
            self.resetCrosshairs()

        self.sigImageChanged.emit()

    def resetCrosshairs(self):
        for child in self.findChildren(SliceableGraphicsView):
            child.resetCrosshair()

    def setPrimary(self, view_dims, slc):
        self.setData(self.data, view_dims, slc, reset_crosshairs=False)

    def updateSlicing(self, slice):
        for widget in self.findChildren(SliceablePanel):
            widget.updateSlicing(slice)

    def setLookupTable(self, lut):
        self.lut = lut
        for image_item in self.getImageItems():
            image_item.setLookupTable(self.lut)

    def setLevels(self, levels):
        self.levels = levels
        for image_item in self.getImageItems():
            image_item.setLevels(levels)

    def getImageItems(self):
        return [child.image_item for child in self.findChildren(SliceableGraphicsView)]

    def getHistogram(self):
        """Returns x and y arrays containing the histogram values for the current image.
                For an explanation of the return format, see numpy.histogram().

                The *step* argument causes pixels to be skipped when computing the histogram to save time.
                If *step* is 'auto', then a step is chosen such that the analyzed data has
                dimensions roughly *targetImageSize* for each axis.

                The *bins* argument and any extra keyword arguments are passed to
                np.histogram(). If *bins* is 'auto', then a bin number is automatically
                chosen based on the image characteristics:

                * Integer images will have approximately *targetHistogramSize* bins,
                  with each bin having an integer width.
                * All other types will have *targetHistogramSize* bins.

                If *perChannel* is True, then the histogram is computed once per channel
                and the output is a list of the results.

                This method is also used when automatically computing levels.
                """
        if self.data is None:
            return None,

        subsample_axes = self.histogram_subsampling_axes
        if not subsample_axes:
            subsample_axes = self.data.dims

        # slices = {axis:slice() for axis in self.data.dims}

        while subsample_axes:
            required_subsampling_factor = max(np.prod(self.data.shape) / self.histogram_max_sample_size, 1.)
            subsampling_per_axis = int(np.round(required_subsampling_factor ** (1 / len(subsample_axes))))

            for axis in subsample_axes:
                # if this axis can't be subsampled (not wide enough)
                if subsampling_per_axis>self.data.shape[self.data.dims.index(axis)]:
                    subsample_axes.remove(axis)
                    continue
            if subsample_axes:
                break
        else:
            raise ValueError('A suitable subsampling over the given axes could not be found.')

        chunking = {axis:slice(None, None, subsampling_per_axis) for axis in subsample_axes}
        print('chunking:', chunking)
        subsampled_data = self.data[chunking]

        hist = np.histogram(subsampled_data)

        return hist[1][:-1], hist[0]

    def channels(self):
        ...


class SliceablePanel(QWidget):
    sigSlicingChanged = Signal(object)
    sigMakePrimary = Signal(object, object)

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
        self.full_view.sigMakePrimary.connect(self.sigMakePrimary)

        if isinstance(parent, SliceablePanel):
            self.full_view.image_item.lut = parent.full_view.image_item.lut
            self.full_view.image_item.levels = parent.full_view.image_item.levels
            self.sigMakePrimary.connect(parent.sigMakePrimary)

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
        self.full_view.crosshair.setPos(slc[view_dims[1]],slc[view_dims[0]])

        if self.right_view:
            self.right_view.setData(data, view_dims=self.getViewDims('right'), slc=slc)

        if self.top_view:
            self.top_view.setData(data, view_dims=self.getViewDims('top'), slc=slc)

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
                self.right_view.show()
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
                self.top_view.show()
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
    sigMakePrimary = Signal(object, object)

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
        self.view.sigMakePrimary.connect(self.sigMakePrimary)

        # Add imageitem
        self.image_item = ImageItem()
        self.view.addItem(self.image_item)

        # add crosshair
        self.crosshair = BetterCrosshairROI((0, 0), parent=self.view, resizable=False)
        self.view.getViewBox().addItem(self.crosshair)

    def setData(self, data):

        xvals = data.coords[data.dims[-1]]
        yvals = data.coords[data.dims[-2]]
        xmin = float(xvals.min())
        xmax = float(xvals.max())
        ymin = float(yvals.min())
        ymax = float(yvals.max())

        # Position the image according to coords
        shape = data.shape
        a = [(0, shape[-1]), (shape[-2] - 1, shape[-1]), (shape[-2] - 1, 1), (0, 1)]

        # b = [(ymin, xmax), (ymax, xmax), (ymax, xmin), (ymin, xmin)]
        b = [(xmax, ymin), (xmax, ymax), (xmin, ymax), (xmin, ymin)]

        quad1 = QPolygonF()
        quad2 = QPolygonF()
        for p, q in zip(a, b):
            quad1.append(QPointF(*p))
            quad2.append(QPointF(*q))

        transform = QTransform()
        QTransform.quadToQuad(quad1, quad2, transform)

        # Bind coords from the xarray to the timeline axis
        # super(SliceableGraphicsView, self).setImage(img, autoRange, autoLevels, levels, axes, np.asarray(img.coords[img.dims[0]]), pos, scale, transform, autoHistogramRange, levelMode)
        self.image_item.setImage(np.asarray(data), autoLevels=False)
        self.image_item.setTransform(transform)

        # Label the image axes
        self.view.setLabel('left', data.dims[-2])
        self.view.setLabel('bottom', data.dims[-1])

    def resetCrosshair(self):
        transform = self.image_item.viewTransform()
        new_pos = transform.map(self.image_item.boundingRect().center())
        self.crosshair.setPos(new_pos)
        self.crosshair.sigMoved.emit(new_pos)

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
    sigMakePrimary = Signal(object, object)

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

        make_primary_action = QAction('Set as Primary View', menu)
        make_primary_action.triggered.connect(self.makePrimary)
        menu.addAction(make_primary_action)

        self._menu = menu

        return menu

    def makePrimary(self):
        self.sigMakePrimary.emit(self.getViewWidget().parent().view_dims, self.getViewWidget().parent().slice)