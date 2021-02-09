import itertools
from functools import partial
import copy
from itertools import zip_longest
from pyqtgraph import ImageView, InfiniteLine, mkPen, ScatterPlotItem, ImageItem, PlotItem, HistogramLUTWidget, \
    GraphicsView, PlotWidget, MultiPlotWidget
from qtpy.QtGui import QTransform, QPolygonF
from qtpy.QtWidgets import QLabel, QErrorMessage, QSizePolicy, QPushButton, QHBoxLayout, QVBoxLayout, QComboBox, \
    QWidget, QMenu, QAction, QGridLayout, QFrame
from qtpy.QtCore import Qt, Signal, Slot, QSize, QPointF, QRectF, QObjectCleanupHandler, QSignalBlocker
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
        self.graphics_view.toggleHorizontalSlice(True)
        self.graphics_view.toggleVerticalSlice(True)
        self.graphics_view.toggleDepthSlice(True)
        self.lut_widget = HistogramLUTWidget(parent=self)
        self.lut_widget.item.setImageItem(self)

        self.graphics_view.sigMakePrimary.connect(self.setPrimary)

        self.layout().addWidget(self.graphics_view)
        self.layout().addWidget(self.lut_widget)

        self.setStyleSheet('NDImageView {background-color:black;}')

    def setData(self, data: DataArray, view_dims=None, slc=None, reset_crosshairs=True):
        self.data = data

        full_slc = {dim: (data.coords[dim].max()-data.coords[dim].min())/2 for dim in data.dims}
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
        for child in self.findChildren(SliceablePanel):
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

    def __init__(self, slice_direction='depth', xlink=None, ylink=None, parent=None):
        super(SliceablePanel, self).__init__(parent=parent)

        assert parent

        self.setLayout(QGridLayout())  # TODO: use splitters
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        self.slice_direction=slice_direction
        self.full_view = ViewSelector(slice_direction, xlink=xlink, ylink=ylink, parent=self)
        self.right_view = None
        self.top_view = None
        self.corner_view = None
        self.data = None
        self.slice = {}
        self.view_dims = None

        self.layout().addWidget(self.full_view, 1, 0, 1, 1)

        for sig, slot in {'sigToggleVerticalSlice': 'toggleVerticalSlice',
                          'sigToggleHorizontalSlice': 'toggleHorizontalSlice',
                          'sigToggleDepthSlice': 'toggleDepthSlice',
                          'sigMakePrimary': 'sigMakePrimary'}.items():
            if hasattr(self.full_view, sig):
                getattr(self.full_view, sig).connect(getattr(self, slot))

        # self.full_view.sigToggleHorizontalSlice.connect(self.toggleHorizontalSlice)
        # self.full_view.sigToggleVerticalSlice.connect(self.toggleVerticalSlice)
        # self.full_view.sigMakePrimary.connect(self.sigMakePrimary)

        # if isinstance(parent, SliceablePanel):
        #     self.full_view.image_item.lut = parent.full_view.image_item.lut
        #     self.full_view.image_item.levels = parent.full_view.image_item.levels
        #     self.sigMakePrimary.connect(parent.sigMakePrimary)

        # Find top-level (NDImageView) widget
        parent = self.parent()
        while not isinstance(parent, NDImageView):
            parent = parent.parent()

        self.sigSlicingChanged.connect(parent.updateSlicing)
        self.full_view.sigCrosshairMoved.connect(self._sliceChangedByCrosshair)

    def _sliceChangedByCrosshair(self):
        view_dims = reversed(self.view_dims)
        crosshair = self.full_view.view_widget.crosshair
        if hasattr(crosshair, 'value'):
            pos = [crosshair.value()]
        else:
            pos = crosshair.pos()

        slc = {key: value for key, value in zip(view_dims, pos)}  # TODO: unify crosshair interface (by passing values through sigs)
        self.sigSlicingChanged.emit(slc)

    @property
    def sliced_data(self):
        slc = {key: value for key, value in self.slice.items() if key not in self.view_dims}
        data = self.data.sel(**slc, method='nearest').transpose(*self.view_dims)
        return data

    def updateSlicing(self, slc):
        self.slice.update(slc)

        self.full_view.setData(self.sliced_data)

        self.updateCrosshair(slc)

    def updateCrosshair(self, slc:dict):
        # update crosshair with the number of dims it wants

        pos = self.slice.copy()

        slc = {dim:slc.get(dim,self.slice[dim]) for dim in self.view_dims}

        # self.full_view.updateCrosshair(*(slc[self.view_dims[i]] for i in reversed(range(self.full_view.supported_ndim))))
        self.full_view.updateCrosshair(*reversed(list(itertools.islice(slc.values(), self.full_view.supported_ndim))))

        # TODO pass slice dicts into updateCrosshair


    def setData(self, data: DataArray, view_dims: Tuple[str], slc: Dict):
        self.data = data
        self.view_dims = view_dims
        self.slice = slc

        self.full_view.setData(self.sliced_data)

        if self.right_view:
            self.right_view.setData(data, view_dims=self.getViewDims('right'), slc=slc)

        if self.top_view:
            self.top_view.setData(data, view_dims=self.getViewDims('top'), slc=slc)

        if self.corner_view:
            self.corner_view.setData(data, view_dims=self.getViewDims('corner'), slc=slc)

    def toggleHorizontalSlice(self, enable):
        if enable:
            if not self.right_view:
                self.right_view = SliceablePanel(slice_direction='horizontal', ylink=self.full_view.view_widget.view.vb, parent=self)
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
                self.top_view = SliceablePanel(slice_direction='vertical', xlink=self.full_view.view_widget.view.vb, parent=self)
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

    def toggleDepthSlice(self, enable):
        if enable:
            if not self.corner_view:
                self.corner_view = SliceablePanel(slice_direction='depth', parent=self)
                if self.data is not None:
                    self.corner_view.setData(self.data, view_dims=self.getViewDims('corner'), slc=self.slice)
                self.layout().addWidget(self.corner_view, 0, 1, 1, 1)
            else:
                self.corner_view.show()
        else:
            self.corner_view.hide()

    def getViewDims(self, quadrant: str) -> Tuple[str, str]:
        depth_index = max(self.data.dims.index(self.view_dims[1]),self.data.dims.index(self.view_dims[0])) + 1

        view_dims = []

        if quadrant == 'right':
            view_dims.append(self.view_dims[0])
            if depth_index<len(self.data.dims):
                view_dims.append(self.data.dims[depth_index])

        elif quadrant == 'top':
            if depth_index<len(self.data.dims):
                view_dims.append(self.data.dims[depth_index])
            view_dims.append(self.view_dims[1])

        elif quadrant == 'corner':
            # NOTE: Not sure these should be reversed
            if depth_index+1 < len(self.data.dims):
                view_dims.append(self.data.dims[depth_index+1])
            if depth_index<len(self.data.dims):
                view_dims.append(self.data.dims[depth_index])

        return tuple(view_dims)

    def resetCrosshair(self):
        self.full_view.resetCrosshair()


# Not strictly necessary, but tracks the required members of a view
class SlicingView():
    def setData(self):
        raise NotImplementedError

    def resetCrosshair(self):
        raise NotImplementedError


class SliceableGraphicsView(GraphicsView, SlicingView):
    sigToggleHorizontalSlice = Signal(bool)
    sigToggleVerticalSlice = Signal(bool)
    sigToggleDepthSlice = Signal(bool)
    sigMakePrimary = Signal(object, object)
    sigCrosshairMoved = Signal()

    SUPPORTED_NDIM = 2

    def __init__(self, slice_direction, parent=None, xlink=None, ylink=None):
        super(SliceableGraphicsView, self).__init__(parent=parent)

        self.slice_direction = slice_direction

        self.setContentsMargins(0, 0, 0, 0)

        # Add axes
        self.view = SliceableAxes(slice_direction)
        self.view.axes["left"]["item"].setZValue(10)
        self.view.axes["top"]["item"].setZValue(10)
        self.setCentralItem(self.view)

        for sig in ['sigToggleVerticalSlice', 'sigToggleHorizontalSlice', 'sigToggleDepthSlice', 'sigMakePrimary']:
            if hasattr(self.view, sig):
                getattr(self.view, sig).connect(getattr(self, sig))

        # Add imageitem
        self.image_item = ImageItem(axisOrder='row-major')
        self.image_item.setOpts()
        self.view.addItem(self.image_item)

        # add crosshair
        self.crosshair = BetterCrosshairROI((0, 0), parent=self.view, resizable=False)
        self.crosshair.sigMoved.connect(self.sigCrosshairMoved)
        self.view.getViewBox().addItem(self.crosshair)

        # find top-level parent NDImageView
        while not isinstance(parent, NDImageView):
            parent = parent.parent()

        # Initialize lut, levels
        self.image_item.setLevels(parent.levels, update=True)
        self.image_item.setLookupTable(parent.lut, update=True)

        # Link axes
        if ylink:
            self.view.vb.setYLink(ylink)
        if xlink:
            self.view.vb.setXLink(xlink)

    def setData(self, data):
        # Constrain squareness when units match
        is_square = data.dims[-2].split('(')[-1] == data.dims[-1].split('(')[-1]
        self.view.vb.setAspectLocked(is_square)

        xvals = data.coords[data.dims[-1]]
        yvals = data.coords[data.dims[-2]]
        xmin = float(xvals.min())
        xmax = float(xvals.max())
        ymin = float(yvals.min())
        ymax = float(yvals.max())

        # Position the image according to coords
        shape = data.shape
        a = [(0, shape[-2]), (shape[-1], shape[-2]), (shape[-1], 0), (0, 0)]

        # b = [(ymin, xmax), (ymax, xmax), (ymax, xmin), (ymin, xmin)]
        if self.slice_direction in ['horizontal', 'depth']:
            b = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]
        elif self.slice_direction=='vertical':
            b = [(xmax, ymax), (xmin, ymax), (xmin, ymin), (xmax, ymin)]

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
        # self.crosshair.sigMoved.emit(new_pos)

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

    def updateCrosshair(self, x, y):
        self.crosshair.setPos(x, y)

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
    sigToggleDepthSlice = Signal(bool)
    sigMakePrimary = Signal(object, object)

    def __init__(self, slice_direction):
        super(SliceableAxes, self).__init__()
        self._menu = None
        self.slice_direction = slice_direction

        # parent_NDImageView = find_parent_NDImageView()
        #
        # self.sigMakePrimary.connect(parent_NDImageView.setPrimary)

    def getContextMenus(self, event):
        if self._menu: return None

        menu = QMenu(parent=self.getViewWidget())
        menu.setTitle("Slicing")

        if self.slice_direction != 'vertical':
            horizontal_action = QAction('Horizontal slice', menu)
            horizontal_action.toggled.connect(self.sigToggleHorizontalSlice)
            horizontal_action.setCheckable(True)
            menu.addAction(horizontal_action)

        if self.slice_direction != 'horizontal':
            vertical_action = QAction('Vertical slice', menu)
            vertical_action.toggled.connect(self.sigToggleVerticalSlice)
            vertical_action.setCheckable(True)
            menu.addAction(vertical_action)

        if self.slice_direction == 'depth':
            depth_action = QAction('Depth slice', menu)
            depth_action.toggled.connect(self.sigToggleDepthSlice)
            depth_action.setCheckable(True)
            menu.addAction(depth_action)

        make_primary_action = QAction('Set as Primary View', menu)
        make_primary_action.triggered.connect(self.makePrimary)
        menu.addAction(make_primary_action)

        self._menu = menu

        return menu

    def makePrimary(self):
        self.sigMakePrimary.emit(self.getViewWidget().parent().parent().parent().view_dims, self.getViewWidget().parent().parent().parent().slice)


class PlotView(PlotWidget):
    sigCrosshairMoved = Signal()  # TODO: crosshairs may actually be emitting their pos; using that would be better

    SUPPORTED_NDIM = 1

    def __init__(self, slice_direction, xlink=None, ylink=None, parent=None):
        super(PlotView, self).__init__(parent=parent)

        self.slice_direction = slice_direction
        self._curve = self.plot()

        if slice_direction == 'horizontal':
            angle=0
        elif slice_direction in ['vertical', 'depth']:
            angle=90
        else:
            raise NotImplementedError
        self.crosshair = InfiniteLine(0, angle=angle, movable=True, markers=[('^', 0), ('v', 1)])
        self.crosshair.sigPositionChanged.connect(self.sigCrosshairMoved)
        self.addItem(self.crosshair)

    def setData(self, data:DataArray):

        reduced_data = data
        # TODO: grab coords and dims and display
        if data.ndim > 1:
            if self.slice_direction == 'horizontal':
                reduced_data = data.sum(data.dims[1:])/(data.size/data.shape[0])
            elif self.slice_direction == 'vertical':
                sum_dims = list(data.dims)  # dims is a tuple, so list gets a copy we can also pop
                sum_dims.pop(1)  # Remove the second dim (being careful about there possibly being 2 or more dims
                reduced_data = data.sum(sum_dims)/(data.size/data.shape[1])

        if self.slice_direction == 'horizontal':
            self._curve.setData(reduced_data, data.coords[data.dims[0]])
            self.plotItem.setLabel('left', data.dims[0])

        elif self.slice_direction in ['vertical', 'depth']:
            if data.ndim == 1:
                dim_index = 0
            else:
                dim_index = 1
            self._curve.setData(data.coords[data.dims[dim_index]], reduced_data)
            self.plotItem.setLabel('bottom', data.dims[dim_index])

    def updateCrosshair(self, *pos):
        with QSignalBlocker(self.crosshair):
            self.crosshair.setPos(pos)

    def resetCrosshair(self):
        if self.slice_direction == 'horizontal':
            data = self._curve.yData
        elif self.slice_direction in ['vertical', 'depth']:
            data = self._curve.xData

        new_pos = (data.max()+data.min())/2

        with QSignalBlocker(self.crosshair):
            self.crosshair.setPos(new_pos)


class ViewSelector(QWidget, SlicingView):
    sigToggleHorizontalSlice = Signal(bool)
    sigToggleVerticalSlice = Signal(bool)
    sigToggleDepthSlice = Signal(bool)
    sigMakePrimary = Signal(object, object)
    sigCrosshairMoved = Signal()

    view_options = {'Image': SliceableGraphicsView,
                    'Plot': PlotView,}

    def __init__(self, slice_direction, default_view_key:str='Image', xlink=None, ylink=None, parent=None):
        super(ViewSelector, self).__init__(parent=parent)

        self.slice_direction = slice_direction
        self.view_widget = None
        self._data = None
        self._crosshair_pos = None

        self.setLayout(QVBoxLayout())

        self.view_frame = QFrame()
        self.view_frame.setLayout(QVBoxLayout())
        self.layout().addWidget(self.view_frame)

        self.selector = QComboBox()
        self.selector.addItems(self.view_options.keys())
        self.selector.currentTextChanged.connect(self._set_view)
        self.layout().addWidget(self.selector)

        self.xlink = xlink
        self.ylink = ylink

        self.set_view(view_key=default_view_key)

    def setData(self, data):
        self._data = data
        if data.ndim < 2 and self.view_widget.SUPPORTED_NDIM == 2:
            # set to 1-d data mode
            self.set_view('Plot')
        self.view_widget.setData(data)

    def set_view(self, view_key):
        self.selector.setCurrentText(view_key)
        self._set_view(view_key)

    def _set_view(self, view_key):
        if self.view_widget is not None:
            self.view_widget.setParent(None)

        self.view_widget = self._make_view(view_key, self.slice_direction, parent=self.view_frame)
        self.view_frame.layout().addWidget(self.view_widget)

        for sig in ['sigToggleHorizontalSlice',
                    'sigToggleVerticalSlice',
                    'sigToggleDepthSlice',
                    'sigMakePrimary',
                    'sigCrosshairMoved']:

            if hasattr(self.view_widget, sig):
                getattr(self.view_widget, sig).connect(getattr(self, sig))

        if self._data is not None:
            self.view_widget.setData(self._data)
        if self._crosshair_pos is not None:
            self.view_widget.updateCrosshair(*self._crosshair_pos)

    def _make_view(self, view_key, slice_direction, parent):
        return self.view_options[view_key](slice_direction=slice_direction, xlink=self.xlink, ylink=self.ylink, parent=parent)

    # def resetCrosshair(self):
    #     transform = self.image_item.viewTransform()
    #     new_pos = transform.map(self.image_item.boundingRect().center())
    #     self.crosshair.setPos(new_pos)
    #     self.crosshair.sigMoved.emit(new_pos)

    def updateCrosshair(self, *pos):
        self._crosshair_pos = pos
        self.view_widget.updateCrosshair(*pos)

    @property
    def supported_ndim(self):
        return self.view_widget.SUPPORTED_NDIM

    def resetCrosshair(self):
        self.view_widget.resetCrosshair()


def find_parent_NDImageView(widget):
    parent = widget.parent()
    while not isinstance(parent, NDImageView):
        parent = parent.parent()
    return parent