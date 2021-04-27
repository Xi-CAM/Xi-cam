# -*- coding: utf-8 -*-
from functools import WRAPPER_ASSIGNMENTS
import pyqtgraph as pg
from pyqtgraph import ImageView, InfiniteLine, mkPen, ScatterPlotItem, ImageItem, PlotItem
from qtpy.QtGui import QTransform, QPolygonF, QIcon, QPixmap
from qtpy.QtWidgets import QLabel, QErrorMessage, QSizePolicy, QPushButton, QHBoxLayout, QVBoxLayout, QComboBox, \
    QWidget, QToolBar, QActionGroup, QAction, QLayout
from qtpy.QtCore import Qt, Signal, Slot, QSize, QPointF, QRectF
import numpy as np
from databroker.core import BlueskyRun

# from pyFAI.geometry import Geometry
from camsaxs.remesh_bbox import remesh, q_from_geometry
from xicam.core import msg
from xicam.core.data import MetaXArray
from xicam.core.data.bluesky_utils import fields_from_stream, streams_from_run, is_image_field
from xicam.gui.actions import ROIAction
from xicam.gui.widgets.elidedlabel import ElidedLabel
from xicam.gui.static import path
from xicam.gui.widgets.ROI import BetterPolyLineROI, BetterCrosshairROI, BetterRectROI, ArcROI, SegmentedArcROI, \
    SegmentedRectROI
import enum
from typing import Callable
from functools import partial

from xicam.plugins import manager as pluginmanager, live_plugin
import inspect


# NOTE: PyQt widget mixins have pitfalls; note #2 here: http://trevorius.com/scrapbook/python/pyqt-multiple-inheritance/

# NOTE: PyFAI geometry position vector is: x = up
#                                          y = right
#                                          z = beam


def q_from_angles(phi, alpha, wavelength):
    r = 2 * np.pi / wavelength
    qx = r * np.sin(phi) * np.cos(alpha)
    qy = r * np.cos(phi) * np.sin(alpha)
    qz = r * (np.cos(phi) * np.cos(alpha) - 1)

    return np.array([qx, qy, qz])


def alpha(x, y, z):
    return np.arctan2(y, z)


def phi(x, y, z):
    return np.arctan2(x, z)


class DisplayMode(enum.Enum):
    raw = enum.auto()
    cake = enum.auto()
    remesh = enum.auto()


class RowMajor(ImageView):
    def __init__(self, *args, **kwargs):
        super(RowMajor, self).__init__(*args, **kwargs)
        self.imageItem.setOpts(replace=True, axisOrder='row-major')


class BetterTicks(ImageView):
    def __init__(self, *args, **kwargs):
        super(BetterTicks, self).__init__(*args, **kwargs)

        # Make ticks span the whole Y range (good for plots)
        self.frameTicks.setYRange([0, 1])

    def setImage(self, img, **kwargs):
        # Only show ticks if they don't drown out everything else
        if img is not None:
            self.frameTicks.setVisible(img.shape[0] < 100)

        super(BetterTicks, self).setImage(img, **kwargs)


class BetterPlots(BetterTicks):
    def __init__(self, *args, **kwargs):
        super(BetterPlots, self).__init__(*args, **kwargs)

        self.ui.roiPlot.setMinimumSize(QSize(0, 200))


class BetterLayout(ImageView):
    # Replaces awkward gridlayout with more structured v/hboxlayouts, and removes useless buttons
    def __init__(self, *args, **kwargs):
        super(BetterLayout, self).__init__(*args, **kwargs)
        self._reset_layout()
        self._set_layout()

    def _set_layout(self, layout=None):
        # Replace the layout
        QWidget().setLayout(self.ui.layoutWidget.layout())
        if layout is not None:
            self.ui.layoutWidget.setLayout(layout)
        else:
            self.ui.layoutWidget.setLayout(self.ui.outer_layout)

    def _reset_layout(self):
        self.ui.outer_layout = QHBoxLayout()
        self.ui.left_layout = QVBoxLayout()
        self.ui.right_layout = QVBoxLayout()
        self.ui.outer_layout.addLayout(self.ui.left_layout)
        self.ui.outer_layout.addLayout(self.ui.right_layout)
        for layout in [self.ui.outer_layout, self.ui.left_layout, self.ui.right_layout]:
            layout.setContentsMargins(0,0,0,0)
            layout.setSpacing(0)

        self.ui.left_layout.addWidget(self.ui.graphicsView)
        self.ui.right_layout.addWidget(self.ui.histogram)

        # Must keep the roiBtn around; ImageView expects to be able to check its state
        self.ui.roiBtn.setParent(self)
        self.ui.roiBtn.hide()



class BetterButtons(BetterLayout):
    def __init__(self, *args, **kwargs):
        super(BetterButtons, self).__init__(*args, **kwargs)

        # Setup axes reset button
        self.resetAxesBtn = QPushButton("Reset Axes")
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.resetAxesBtn.sizePolicy().hasHeightForWidth())
        self.resetAxesBtn.setSizePolicy(sizePolicy)
        self.resetAxesBtn.setObjectName("resetAxes")
        self.ui.right_layout.addWidget(self.resetAxesBtn)
        self.resetAxesBtn.clicked.connect(self.autoRange)

        # Setup LUT reset button
        self.resetLUTBtn = QPushButton("Reset LUT")
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.resetLUTBtn.sizePolicy().hasHeightForWidth())
        # self.resetLUTBtn.setSizePolicy(sizePolicy)
        # self.resetLUTBtn.setObjectName("resetLUTBtn")
        self.ui.right_layout.addWidget(self.resetLUTBtn)
        self.resetLUTBtn.clicked.connect(self.autoLevels)


class ExportButton(BetterLayout):
    def __init__(self, *args, **kwargs):
        super(ExportButton, self).__init__(*args, **kwargs)

        # Export button
        self.exportBtn = QPushButton('Export')
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.exportBtn.sizePolicy().hasHeightForWidth())
        self.ui.right_layout.addWidget(self.exportBtn)
        self.exportBtn.clicked.connect(self.export)


@live_plugin('ImageMixinPlugin')
class XArrayView(ImageView):
    def __init__(self, *args, **kwargs):
        # Add axes
        self.axesItem = PlotItem()
        self.axesItem.axes["left"]["item"].setZValue(10)
        self.axesItem.axes["top"]["item"].setZValue(10)

        if "view" not in kwargs:
            kwargs["view"] = self.axesItem

        super(XArrayView, self).__init__(*args, **kwargs)

        self.view.invertY(False)

    def setImage(self, img, **kwargs):

        if hasattr(img, 'coords'):

            if 'transform' not in kwargs:

                xvals = img.coords[img.dims[-2]]
                yvals = img.coords[img.dims[-1]]
                xmin = float(xvals.min())
                xmax = float(xvals.max())
                ymin = float(yvals.min())
                ymax = float(yvals.max())

                # Position the image according to coords
                shape = img.shape
                a = [(0, shape[-2]), (shape[-1]-1, shape[-2]), (shape[-1]-1, 1), (0, 1)]

                b = [(ymin, xmin), (ymax, xmin), (ymax, xmax), (ymin, xmax)]

                quad1 = QPolygonF()
                quad2 = QPolygonF()
                for p, q in zip(a, b):
                    quad1.append(QPointF(*p))
                    quad2.append(QPointF(*q))

                transform = QTransform()
                QTransform.quadToQuad(quad1, quad2, transform)

                kwargs['transform'] = transform

            if 'xvals' not in kwargs:
                kwargs['xvals'] = np.asarray(img.coords[img.dims[0]])

            # Set the timeline axis label from dims
            self.ui.roiPlot.setLabel('bottom', img.dims[0])

            # Label the image axes
            self.axesItem.setLabel('left', img.dims[-2])
            self.axesItem.setLabel('bottom', img.dims[-1])

            # Add a bit more size
            self.ui.roiPlot.setMinimumSize(QSize(0, 70))

        # Bind coords from the xarray to the timeline axis
        super(XArrayView, self).setImage(img, **kwargs)

    def updateImage(self, autoHistogramRange=True):
        if hasattr(self.image, 'dims'):
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

            if not isinstance(image, Pseudo3DFrameArray):
                axorder = [self.axes[ax] for ax in axorder if self.axes[ax] is not None]
                ax_swap = [image.dims[ax_index] for ax_index in axorder]
                image = image.transpose(*ax_swap)

            # Select time index
            if self.axes['t'] is not None:
                self.ui.roiPlot.show()
                image = image[self.currentIndex]

            self.imageItem.updateImage(np.asarray(image))

        else:
            super(XArrayView, self).updateImage(autoHistogramRange)

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


class PixelSpace(XArrayView, RowMajor):
    def __init__(self, *args, **kwargs):
        # Add axes
        self.axesItem = PlotItem()
        self.axesItem.axes["left"]["item"].setZValue(10)
        self.axesItem.axes["top"]["item"].setZValue(10)
        if "view" not in kwargs:
            kwargs["view"] = self.axesItem

        self._transform = QTransform()

        super(PixelSpace, self).__init__(*args, **kwargs)

        self.imageItem.sigImageChanged.connect(self.updateAxes)

    def transform(self, img=None):
        # Build Quads
        shape = img.shape
        a = [(0, shape[-2] - 1), (shape[-1] - 1, shape[-2] - 1), (shape[-1] - 1, 0), (0, 0)]

        b = [(0, 1), (shape[-1] - 1, 1), (shape[-1] - 1, shape[-2]), (0, shape[-2])]

        quad1 = QPolygonF()
        quad2 = QPolygonF()
        for p, q in zip(a, b):
            quad1.append(QPointF(*p))
            quad2.append(QPointF(*q))

        transform = QTransform()
        QTransform.quadToQuad(quad1, quad2, transform)

        for item in self.view.items:
            if isinstance(item, ImageItem):
                item.setTransform(transform)
        self._transform = transform
        return transform

    def setImage(self, img, *args, **kwargs):
        if img is None:
            return

        if not kwargs.get("transform", None):
            transform = self.transform(img)
            self.updateAxes()
            super(PixelSpace, self).setImage(img, *args, transform=transform, **kwargs)

        else:
            super(PixelSpace, self).setImage(img, *args, **kwargs)

    def setTransform(self):
        self.setImage(self.image)  # this should loop back around to the respective transforms

    def updateAxes(self):
        self.axesItem.setLabel("bottom", "x (px)")  # , units='s')
        self.axesItem.setLabel("left", "z (px)")


class QSpace(PixelSpace):
    def __init__(self, *args, geometry=None, **kwargs):
        self.displaymode = DisplayMode.raw
        self._geometry = None  # type: AzimuthalIntegrator

        super(QSpace, self).__init__(*args, **kwargs)

        self.setGeometry(geometry)

    def setGeometry(self, geometry):
        if callable(geometry):
            geometry = geometry()
        self._geometry = geometry
        self.setTransform()

    def setImage(self, img, *args, geometry=None, **kwargs):
        if geometry:
            self.setGeometry(geometry)
        super(QSpace, self).setImage(img, *args, **kwargs)


class Pseudo3DFrameArray(object):
    """Array that pretends it is a 3D array, but really only has one frame.

    Data passed into it should be the already sliced (single-frame) array.
    """
    def __init__(self, data):
        self.data = data
        self.dims = []

    def transpose(self, *args, **kwargs):
        return self

    def __getitem__(self, item):
        """Override getitem to pretend it is a 3D array.

        Ignores the item slice and return the contained frame data."""
        return self.data


class ProcessingView(pg.ImageView):
    def getProcessedImage(self):
        self._imageLevels = self.quickMinMax(self.image)

        # FIXME: do all incoming images need to be treated as Pseudo3DFrameArrays?
        #   - (1, X, Y) vs (X, Y) images
        image = self.image
        if image.ndim == 3:
            image = Pseudo3DFrameArray(self.process(np.array(image[self.currentIndex])))

        self.levelMin, self.levelMax = self.process_levels(self._imageLevels)

        return image

    def process(self, image):
        raise NotImplementedError

    def process_levels(self, levels):
        level_min = min([level[0] for level in self._imageLevels])
        level_max = max([level[1] for level in self._imageLevels])

        return level_min, level_max


class CenterMarker(QSpace):
    def __init__(self, *args, **kwargs):
        self.centerplot = ScatterPlotItem(brush="r")
        self.centerplot.setZValue(100)

        super(CenterMarker, self).__init__(*args, **kwargs)

        self.addItem(self.centerplot)
        self.drawCenter()

    def drawCenter(self):
        try:
            fit2d = self._geometry.getFit2D()
        except (TypeError, AttributeError):
            pass
        else:
            if self.imageItem.image is not None:
                if self.displaymode == DisplayMode.raw:
                    x = fit2d["centerX"]
                    y = fit2d["centerY"]
                    self.centerplot.setData(x=[x], y=[y])
                elif self.displaymode == DisplayMode.remesh:
                    self.centerplot.setData(x=[0], y=[0])

    def setGeometry(self, geometry):
        super(CenterMarker, self).setGeometry(geometry)
        self.drawCenter()


class Crosshair(ImageView):
    def __init__(self, *args, **kwargs):
        super(Crosshair, self).__init__(*args, **kwargs)
        linepen = mkPen("#FFA500")
        self._vline = InfiniteLine((0, 0), angle=90, movable=False, pen=linepen)
        self._hline = InfiniteLine((0, 0), angle=0, movable=False, pen=linepen)

        self._vline.setVisible(False)
        self._hline.setVisible(False)

        self.addItem(self._vline)
        self.addItem(self._hline)

        self.scene.sigMouseMoved.connect(self.moveCrosshair)

    def moveCrosshair(self, pos):
        if self.view.getViewBox().sceneBoundingRect().contains(pos):
            mousePoint = self.view.getViewBox().mapSceneToView(pos)
            x, y = mousePoint.x(), mousePoint.y()

            if self.imageItem.mapRectToView(self.imageItem.boundingRect()).contains(mousePoint):  # within bounds
                self._vline.setPos(x)
                self._hline.setPos(y)
                self._hline.setVisible(True)
                self._vline.setVisible(True)
            else:
                self._hline.setVisible(False)
                self._vline.setVisible(False)


class PixelCoordinates(PixelSpace, BetterLayout):
    def __init__(self, *args, **kwargs):
        super(PixelCoordinates, self).__init__(*args, **kwargs)

        self._coordslabel = QLabel(parent=self)

        font = self._coordslabel.font()
        font.setPixelSize(14)
        self._coordslabel.setFont(font)

        self.ui.left_layout.addWidget(self._coordslabel, alignment=Qt.AlignHCenter)
        self.ui.right_layout.setSizeConstraint(QLayout.SetMinAndMaxSize)

        # Accommodate vertical height
        self._coordslabel.setMinimumSize(self._coordslabel.minimumSize().width(),
                                         self._coordslabel.minimumHeight() + self._coordslabel.height())

        self.scene.sigMouseMoved.connect(self.displayCoordinates)

    def displayCoordinates(self, pos):
        if self.view.sceneBoundingRect().contains(pos):
            mousePoint = self.view.getViewBox().mapSceneToView(pos)
            pos = QPointF(mousePoint.x(), mousePoint.y())

            if self.imageItem.mapRectToView(self.imageItem.boundingRect()).contains(mousePoint):  # within bounds
                # angstrom=QChar(0x00B5)
                pxpos = self.imageItem.mapFromView(pos)

                self.formatCoordinates(pxpos, pos)
            else:
                self._coordslabel.setText("")

    def formatCoordinates(self, pxpos, pos):
        """
        when the mouse is moved in the viewer, recalculate coordinates
        """

        try:
            I = self.imageItem.image[int(pxpos.y()), int(pxpos.x())]
        except IndexError:
            I = 0

        self._coordslabel.setText(f"x={pxpos.x():0.1f} y={pxpos.y():0.1f} I={I:0.0f}")


class QCoordinates(QSpace, PixelCoordinates):

    def formatCoordinates(self, pxpos, pos):

        """
        when the mouse is moved in the viewer, recalculate coordinates
        """

        if self._geometry:
            if self.displaymode == DisplayMode.remesh:
                try:
                    I = self.imageItem.image[int(pxpos.y()), int(pxpos.x())]
                except IndexError:
                    I = 0
                self._coordslabel.setText(
                    f"x={pxpos.x():0.1f}, "
                    f"y={self.imageItem.image.shape[-2] - pxpos.y():0.1f}, "
                    f"I={I:0.0f}, "
                    f"q={np.sqrt(pos.x() ** 2 + pos.y() ** 2):0.3f} \u212B\u207B\u00B9, "
                    f"q<sub>z</sub>={pos.y():0.3f} \u212B\u207B\u00B9, "
                    f"q<sub>\u2225</sub>={pos.x():0.3f} \u212B\u207B\u00B9, "
                    f"d={2 * np.pi / np.sqrt(pos.x() ** 2 + pos.y() ** 2) * 10:0.3f} nm, "
                    f"\u03B8={np.rad2deg(np.arctan2(pos.y(), pos.x())):.2f}&#176;"
                )
            elif self.displaymode == DisplayMode.raw:
                try:
                    I = self.imageItem.image[int(pxpos.y()), int(pxpos.x())]
                except IndexError:
                    I = 0

                q = q_from_geometry(self.imageItem.image.shape,
                                    self._geometry,
                                    reflection=False,
                                    alphai=0)[int(pxpos.y()), int(pxpos.x())]

                self._coordslabel.setText(
                    f"x={pxpos.x():0.1f}, "
                    f"y={self.imageItem.image.shape[-2] - pxpos.y():0.1f}, "
                    f"I={I:0.0f}, "
                    f"q={np.sqrt(np.sum(np.square(q))):0.3f} \u212B\u207B\u00B9, "
                    f"q<sub>z</sub>={q[1]:0.3f} \u212B\u207B\u00B9, "
                    f"q<sub>\u2225</sub>={q[0]:0.3f} \u212B\u207B\u00B9, "
                    f"d={2 * np.pi / np.sqrt(q[0] ** 2 + q[1] ** 2) * 10:0.3f} nm, "
                    f"\u03B8={np.rad2deg(np.arctan2(q[1], q[0])):.2f}&#176;"
                )
        else:
            super(QCoordinates, self).formatCoordinates(pxpos, pos)


class PolygonROI(ImageView):
    def __init__(self, *args, **kwargs):
        """
        Image view extended with an adjustable polygon region-of-interest (ROI).

        When first displayed, the polygon ROI's corners will be set to the image item's corners.

        Parameters
        ----------
        args, optional
            Positional arguments for the ImageView.
        kwargs, optional
            Keyword arguments for the ImageView.
        """
        super(PolygonROI, self).__init__(*args, **kwargs)
        rect = self.imageItem.boundingRect()  # type: QRectF
        positions = [
            (rect.bottomLeft().x(), rect.bottomLeft().y()),
            (rect.bottomRight().x(), rect.bottomRight().y()),
            (rect.topRight().x(), rect.topRight().y()),
            (rect.topLeft().x(), rect.topLeft().y()),
        ]
        self._roiItem = BetterPolyLineROI(positions=positions, closed=True, scaleSnap=True, translateSnap=True)
        self.addItem(self._roiItem)

    def __repr__(self):
        return type(self).__name__ + repr(self._roiItem)

    def poly_mask(self):
        """
        Gets the mask array for a ROI polygon on the image.

        The mask array's shape will match the image's shape.
        Any pixel inside both the ROI polygon and the image will be set to 1 in the mask array;
        all other values in the mask will be set to 0.

        Returns
        -------
        ndarray:
            Mask array of the ROI polygon within image space (mask shape matches image shape).

        """
        result, mapped = self._roiItem.getArrayRegion(
            np.ones_like(self.imageItem.image), self.imageItem, returnMappedCoords=True
        )

        # TODO -- move this code to own function and test
        # Reverse the result array to make indexing calculations easier, then revert back
        result = result[::-1, ::-1]
        mapped = mapped[::-1, ::-1]

        # Pad result mask rect into bounding rect of mask and image
        floorRow = np.floor(mapped[0]).astype(int)
        floorCol = np.floor(mapped[1]).astype(int)

        # Return empty mask if ROI bounding box does not intersect image bounding box
        resultRect = QRectF(QPointF(np.min(floorRow), np.min(floorCol)), QPointF(np.max(floorRow), np.max(floorCol)))
        if not self._intersectsImage(resultRect):
            # TODO -- is zeros(shape) the right return value for a non-intersecting polygon?
            return np.zeros(self.imageItem.image.shape)

        # Find the bounds of the ROI polygon
        minX = np.min(floorRow)
        maxX = np.max(floorRow)
        minY = np.min(floorCol)
        maxY = np.max(floorCol)

        width = self.imageItem.width()
        height = self.imageItem.height()
        # Pad the ROI polygon into the image shape
        # Don't need padding if a polygon boundary is outside of the image shape
        padXBefore = minX
        if minX < 0:
            padXBefore = 0
        padXAfter = height - maxX
        if padXAfter < 0:
            padXAfter = 0
        padYBefore = minY
        if minY < 0:
            padYBefore = 0
        padYAfter = width - maxY
        if padYAfter < 0:
            padYAfter = 0

        boundingBox = np.pad(result, ((padYBefore, padYAfter), (padXBefore, padXAfter)), "constant")

        # For trimming, any negative minimums need to be shifted into the image shape
        offsetX = 0
        offsetY = 0
        if minX < 0:
            offsetX = abs(minX)
        if minY < 0:
            offsetY = abs(minY)
        trimmed = boundingBox[abs(offsetY) : abs(offsetY) + height, abs(offsetX) : abs(offsetX) + width]

        # Reorient the trimmed mask array
        trimmed = trimmed[::-1, ::-1]

        # # TODO remove plotting code below
        # from matplotlib import pyplot as plt
        # plt.figure('bounding_box, origin="lower"')
        # plt.imshow(boundingBox, origin='lower')
        # plt.show()
        #
        #
        # plt.figure(f'trimmed, origin="lower", [{abs(offsetY)}:{abs(offsetY)+height}, {abs(offsetX)}:{abs(offsetX)+width}]')
        # plt.imshow(trimmed, origin='lower')
        # plt.show()
        # # TODO remove the plotting code above
        return trimmed

    def _intersectsImage(self, rectangle: QRectF):
        """
        Checks if a rectangle intersects the image's bounding rectangle.

        Parameters
        ----------
        rectangle
            Rectangle to test intersection with the image item's bounding rectangle.

        Returns
        -------
        bool
            True if the rectangle and the image bounding rectangle intersect; otherwise False.

        """
        # TODO -- test
        return self.imageItem.boundingRect().intersects(rectangle)


import collections
from pyqtgraph import functions as fn
from pyqtgraph import debug
from pyqtgraph import Point


class ComposableItemImageView(ImageView):
    """
    Used to compose together different image view mixins that may use different ItemImage subclasses.
    See LogScaleIntensity, LogScaleImageItem, ImageViewHistogramOverflowFIx, ImageItemHistorgramOverflowFix.
    Note that any imageItem named argument passed into the ImageView mixins above will discard the item and instead
    create a composition of imageItem_bases with their respective ImageItem class.
    """

    imageItem_bases = tuple()


class LogScaleImageItem(ImageItem):
    def __init__(self, *args, **kwargs):
        super(LogScaleImageItem, self).__init__(*args, **kwargs)
        self.logScale = True

    def render(self):
        # Convert data to QImage for display.

        profile = debug.Profiler()
        if self.image is None or self.image.size == 0:
            return
        if isinstance(self.lut, collections.Callable):
            lut = self.lut(self.image)
        else:
            lut = self.lut

        if self.logScale:
            image = self.image + 1
            with np.errstate(invalid="ignore", divide='ignore'):
                image = image.astype(np.float)
                np.log(image, where=image >= 0, out=image)  # map to 0-255
        else:
            image = self.image

        if self.autoDownsample:
            # reduce dimensions of image based on screen resolution
            o = self.mapToDevice(QPointF(0, 0))
            x = self.mapToDevice(QPointF(1, 0))
            y = self.mapToDevice(QPointF(0, 1))
            w = Point(x - o).length()
            h = Point(y - o).length()
            if w == 0 or h == 0:
                self.qimage = None
                return
            xds = max(1, int(1.0 / w))
            yds = max(1, int(1.0 / h))
            axes = [1, 0] if self.axisOrder == "row-major" else [0, 1]
            image = fn.downsample(image, xds, axis=axes[0])
            image = fn.downsample(image, yds, axis=axes[1])
            self._lastDownsample = (xds, yds)
        else:
            pass

        # if the image data is a small int, then we can combine levels + lut
        # into a single lut for better performance
        levels = self.levels
        if levels is not None and levels.ndim == 1 and image.dtype in (np.ubyte, np.uint16):
            if self._effectiveLut is None:
                eflsize = 2 ** (image.itemsize * 8)
                ind = np.arange(eflsize)
                minlev, maxlev = levels
                levdiff = maxlev - minlev
                levdiff = 1 if levdiff == 0 else levdiff  # don't allow division by 0
                if lut is None:
                    efflut = fn.rescaleData(ind, scale=255.0 / levdiff, offset=minlev, dtype=np.ubyte)
                else:
                    lutdtype = np.min_scalar_type(lut.shape[0] - 1)
                    efflut = fn.rescaleData(
                        ind, scale=(lut.shape[0] - 1) / levdiff, offset=minlev, dtype=lutdtype, clip=(0, lut.shape[0] - 1)
                    )
                    efflut = lut[efflut]

                self._effectiveLut = efflut
            lut = self._effectiveLut
            levels = None

        # Assume images are in column-major order for backward compatibility
        # (most images are in row-major order)

        if self.axisOrder == "col-major":
            image = image.transpose((1, 0, 2)[: image.ndim])

        if self.logScale:
            with np.errstate(invalid="ignore"):
                levels = np.log(np.add(levels, 1))
            levels[0] = np.nanmax([levels[0], 0])

        argb, alpha = fn.makeARGB(image, lut=lut, levels=levels)
        self.qimage = fn.makeQImage(argb, alpha, transpose=False)


class LogScaleIntensity(BetterLayout, ComposableItemImageView):
    def __init__(self, *args, log_scale=True, **kwargs):
        # Composes a new type consisting of any ImageItem types in imageItem_bases with this classes's helper ImageItem
        # class (LogScaleImageItem)
        self.imageItem_bases += (LogScaleImageItem,)
        imageItem = type("DynamicImageItem", tuple(self.imageItem_bases), {})()
        if "imageItem" in kwargs:
            del kwargs["imageItem"]
        super(LogScaleIntensity, self).__init__(imageItem=imageItem, *args, **kwargs)


        self.logScale = log_scale

        # Setup log scale button
        self.logIntensityButton = QPushButton("Log Intensity")
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.logIntensityButton.sizePolicy().hasHeightForWidth())
        self.logIntensityButton.setSizePolicy(sizePolicy)
        self.logIntensityButton.setObjectName("logIntensity")
        self.ui.right_layout.addWidget(self.logIntensityButton)
        self.logIntensityButton.setCheckable(True)
        self.setLogScale(self.logScale)
        self.logIntensityButton.clicked.connect(self._setLogScale)

    def _setLogScale(self, value):
        self.imageItem.logScale = value
        self.imageItem.qimage = None
        self.imageItem.update()
        self.getHistogramWidget().region.setBounds([0 if value else None, None])

    def setLogScale(self, value):
        self._setLogScale(value)
        self.logIntensityButton.setChecked(value)


class CatalogView(XArrayView):
    sigCatalogChanged = Signal(BlueskyRun)
    sigStreamChanged = Signal(str)
    sigFieldChanged = Signal(str)

    def __init__(self, catalog=None, stream=None, field=None, *args, **kwargs):
        self.catalog = catalog
        self.stream = stream
        self.field = field
        super(CatalogView, self).__init__(*args, **kwargs)
        self.setCatalog(self.catalog, self.stream, self.field)

    def setCatalog(self, catalog, stream=None, field=None, *args, **kwargs):
        self.catalog = catalog
        self.stream = stream
        self.field = field
        if not catalog:
            return
        if not field:
            try:
                field = catalog.metadata['start']['detectors'][0]
            except Exception as ex:
                msg.logError(ex)
            self.field = field
        self._updateCatalog(*args, **kwargs)

    def _updateCatalog(self, *args, **kwargs):
        if all([self.catalog, self.stream, self.field]):
            try:
                stream = getattr(self.catalog, self.stream)
            except AttributeError as ex:
                msg.logError(ex)
                return

            eventStream = stream.to_dask()[self.field]

            # Trim off event dimension (so transpose works)
            if eventStream.ndim > 3:
                if eventStream.shape[0] == 1:  # if only one event, drop the event axis
                    eventStream = eventStream[0]
                if eventStream.shape[1] == 1:  # if z axis is unitary, drop that axis
                    eventStream = eventStream[:, 0]
            self.xarray = eventStream
            self.setImage(img=self.xarray, *args, **kwargs)
        else:
            # TODO -- clear the current image
            pass

    def setStream(self, stream):
        self.clear()
        self.stream = stream
        self._updateCatalog()
        self.sigStreamChanged.emit(stream)

    def setField(self, field):
        self.clear()
        self.field = field
        self._updateCatalog()
        # TODO -- figure out where to put the geometry update
        if QSpace in inspect.getmro(type(self)):
            self.setGeometry(pluginmanager.get_plugin_by_name("xicam.SAXS.calibration", "SettingsPlugin").AI(field))
        self.sigFieldChanged.emit(field)


class CrosshairROI(ImageView):

    def __init__(self, *args, **kwargs):
        super(CrosshairROI, self).__init__(*args, **kwargs)

        self.crosshair = BetterCrosshairROI(parent=self.view)

    def setImage(self, *args, reset_crosshair=True, **kwargs):
        super(CrosshairROI, self).setImage(*args, **kwargs)

        if reset_crosshair:
            transform = self.imageItem.viewTransform()
            new_pos = transform.map(self.imageItem.boundingRect().center())
            self.crosshair.setPos(new_pos)
            self.crosshair.sigMoved.emit(new_pos)

        # Must autorange again, since crosshair just moved
        if kwargs.get('autoRange'):
            self.autoRange()


class DepthPlot(XArrayView, CrosshairROI):
    def __init__(self, *args, **kwargs):
        super(DepthPlot, self).__init__()

        # self.roi = pg.RectROI((0,0), (1,1))
        # self.region_roi = pg.RectROI((0,0), (1,1))

        self.crosshair.sigMoved.connect(self.plotDepth)
        self._plotitem = self.ui.roiPlot.plot()  # type: pg.PlotDataItem

    def plotDepth(self):
        x, y = self.crosshair.pos()
        self._plotitem.setData(x=np.asarray(self.image.coords[self.image.dims[0]]),
                               y=self.image.sel(**{self.image.dims[2]: x, self.image.dims[1]: y}, method='nearest'))


class StreamSelector(CatalogView, BetterLayout):
    def __init__(self, *args, stream_filter=None, **kwargs):
        self.stream_filter = stream_filter
        self.streamComboBox = QComboBox()
        super(StreamSelector, self).__init__(*args, **kwargs)
        self.ui.right_layout.insertWidget(0, self.streamComboBox)
        self.streamComboBox.currentTextChanged.connect(self.setStream)

    def setCatalog(self, catalog, stream=None, field=None, *args, **kwargs):
        stream = self.updateStreamNames(catalog)
        super(StreamSelector, self).setCatalog(catalog, stream, field, *args, **kwargs)

    def updateStreamNames(self, catalog):
        self.streamComboBox.clear()
        if catalog:
            streams = streams_from_run(catalog)
            if self.stream_filter:
                streams = list(filter(is_image_field, streams))
            self.streamComboBox.addItems(streams)
        return self.streamComboBox.currentText()


class FieldSelector(CatalogView, BetterLayout):
    def __init__(self, *args, field_filter: Callable = is_image_field, **kwargs):
        self.field_filter = field_filter
        self.fieldComboBox = QComboBox()
        super(FieldSelector, self).__init__(*args, **kwargs)

        self.ui.right_layout.insertWidget(0, self.fieldComboBox)
        self.fieldComboBox.currentTextChanged.connect(self.setField)

    def setCatalog(self, catalog, stream=None, field=None, *args, **kwargs):
        field = self.updateFieldNames(catalog, stream)
        super(FieldSelector, self).setCatalog(catalog, stream, field, *args, **kwargs)

    def setStream(self, stream_name):
        self.stream = stream_name
        self.updateFieldNames(self.catalog, stream_name)
        super(FieldSelector, self).setStream(stream_name)

    def updateFieldNames(self, catalog, stream):
        self.fieldComboBox.clear()
        if catalog and stream:
            fields = fields_from_stream(catalog, stream)
            if self.field_filter:
                fields = list(filter(partial(self.field_filter, catalog, stream), fields))
            self.fieldComboBox.addItems(fields)
        return self.fieldComboBox.currentText()


class CatalogImagePlotView(StreamSelector, FieldSelector):
    def __init__(self, catalog=None, stream=None, field=None, *args, **kwargs):
        # Turn off image field filtering for this mixin
        super(CatalogImagePlotView, self).__init__(catalog, stream, field, *args, **kwargs)

    def setData(self, data, *args, **kwargs):
        self.axesItem.clearPlots()
        if len(data.shape) == 1:
            self.ui.roiPlot.hide()
            self.ui.histogram.hide()
            self.view.removeItem(self.imageItem)
            self.axesItem.plot(y=data, *args, **kwargs)
            if "labels" in kwargs:
                self.axesItem.setLabels(**kwargs['labels'])
            self.view.enableAutoRange(x=True, y=True)
            self.view.setAspectLocked(False)
        else:
            self.view.addItem(self.imageItem)
            self.setImage(data)
            self.ui.roiPlot.show()
            self.ui.histogram.show()
            self.view.setAspectLocked(True)

    def _updateCatalog(self, *args, **kwargs):
        if all([self.catalog, self.stream, self.field]):
            try:
                stream = getattr(self.catalog, self.stream)
            except AttributeError as ex:
                msg.logError(ex)
                return

            eventStream = stream.to_dask()[self.field]

            self.xarray = np.squeeze(eventStream)

            kwargs['antialias'] = True
            kwargs['pen'] = pg.mkPen(width=2)
            kwargs['symbol'] = 'o'
            kwargs['labels'] = {'left': self.field}

            try:
                scan_axis_field_name = self.catalog.metadata['start']['hints']['dimensions'][0][0][0]
            except Exception as ex:
                msg.logError(ex)
            else:
                kwargs['x'] = stream.to_dask()[scan_axis_field_name]
                kwargs['labels']['bottom'] = scan_axis_field_name

            self.setData(data=self.xarray, *args, **kwargs)
        else:
            # TODO -- clear the current image
            pass


class ImageItemHistogramOverflowFix(ImageItem):
    def getHistogram(self, bins="auto", step="auto", targetImageSize=200, targetHistogramSize=500, **kwds):
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

                This method is also used when automatically computing levels.
                """
        if self.image is None:
            return None, None
        if step == "auto":
            step = (int(np.ceil(self.image.shape[0] / targetImageSize)), int(np.ceil(self.image.shape[1] / targetImageSize)))
        if np.isscalar(step):
            step = (step, step)
        stepData = self.image[:: step[0], :: step[1]]

        if bins == "auto":
            if stepData.dtype.kind in "ui":
                mn = stepData.min()
                mx = stepData.max()
                # print(f"\n*** mx, mn: {mx}, {mn} ({type(mx)}, {type(mn)})***\n")
                # PATCH -- explicit subtract with np.int to avoid overflow
                step = max(1, np.ceil(np.subtract(mx, mn, dtype=np.int) / 500.0))
                bins = np.arange(mn, mx + 1.01 * step, step, dtype=np.int)
                if len(bins) == 0:
                    bins = [mn, mx]
            else:
                bins = 500

        kwds["bins"] = bins
        stepData = stepData[np.isfinite(stepData)]
        hist = np.histogram(stepData, **kwds)

        return hist[1][:-1], hist[0]


class ImageViewHistogramOverflowFix(ComposableItemImageView):
    def __init__(self, *args, **kwargs):
        self.imageItem_bases += (ImageItemHistogramOverflowFix,)
        # Create a dynamic image item type, composing existing ImageItem classes with this classes's appropriate
        # ImageItem class (ImageItemHistogramOverflowFix)
        imageItem = type("DynamicImageItem", tuple(self.imageItem_bases), {})()
        if "imageItem" in kwargs:
            del kwargs["imageItem"]
        super(ImageViewHistogramOverflowFix, self).__init__(imageItem=imageItem, *args, **kwargs)


@live_plugin('ImageMixinPlugin')
class SliceSelector(BetterLayout):

    def __init__(self, *args, **kwargs):
        super(SliceSelector, self).__init__(*args, **kwargs)

        self.slice_selector = QComboBox()
        self.slice_selector.currentIndexChanged.connect(self.setCurrentIndex)
        self.ui.right_layout.addWidget(self.slice_selector)
        self.ui.roiPlot.setVisible(False)

    def setImage(self, img, *args, **kwargs):
        super(SliceSelector, self).setImage(img, *args, **kwargs)
        self.ui.roiPlot.setVisible(False)
        self.slice_selector.clear()
        self.slice_selector.addItems(list(map(str, self.tVals.ravel())))

    def setCurrentIndex(self, ind):
        super(SliceSelector, self).setCurrentIndex(ind)
        self.ui.roiPlot.setVisible(False)


@live_plugin("ImageMixinPlugin")
class ToolbarLayout(BetterLayout):
    """Mixin to support a toolbar at the top of the ImageView.

    Can pass in the toolbar you want via `toolbar`,
    and can modify toolbar via the `toolbar` attribute.
    """
    def __init__(self, *args, toolbar=None, **kwargs):
        super(ToolbarLayout, self).__init__(*args, **kwargs)
        self.toolbar = toolbar or QToolBar()

        # Define new layout
        self.toolbar_outer_layout = QVBoxLayout()
        self.toolbar_outer_layout.addWidget(self.toolbar)

        # Reinitialize the better layout
        self._reset_layout()  # FIXME: Find a way to remove this to prevent sensitivity to order of inheritance

        # Create new layout hierarchy (in this case, a new outer_layout that contains the original layouts within)
        outer_layout = self.ui.outer_layout
        self.toolbar_outer_layout.addLayout(outer_layout)
        self._set_layout(self.toolbar_outer_layout)

    def mkAction(self, iconpath: str = None, text=None, receiver=None, group=None, checkable=False, checked=False):
        actn = QAction(self)
        if iconpath: actn.setIcon(QIcon(QPixmap(str(path(iconpath)))))
        if text: actn.setText(text)
        if receiver: actn.triggered.connect(receiver)
        actn.setCheckable(checkable)
        if checked: actn.setChecked(checked)
        if group: actn.setActionGroup(group)
        return actn


class EwaldCorrected(QSpace, RowMajor, ToolbarLayout, ProcessingView):
    def __init__(self, *args, **kwargs):
        self.geometry_mode = 'transmission'
        self.incidence_angle = 0

        super(EwaldCorrected, self).__init__(*args, **kwargs)

        self.mode_group = QActionGroup(self)
        self.raw_action = self.mkAction('icons/raw.png', 'Raw', checkable=True, group=self.mode_group, checked=True)
        self.toolbar.addAction(self.raw_action)
        self.raw_action.triggered.connect(partial(self.setDisplayMode, DisplayMode.raw))
        self.cake_action = self.mkAction('icons/cake.png', 'Cake (q/chi plot)', checkable=True, group=self.mode_group)
        self.toolbar.addAction(self.cake_action)
        self.cake_action.triggered.connect(partial(self.setDisplayMode, DisplayMode.cake))
        self.remesh_action = self.mkAction('icons/remesh.png', 'Wrap Ewald Sphere', checkable=True,
                                           group=self.mode_group)
        self.toolbar.addAction(self.remesh_action)
        self.remesh_action.triggered.connect(partial(self.setDisplayMode, DisplayMode.remesh))

        # Disable these views initially, if geometry gets set, they will be enabled
        self.cake_action.setEnabled(False)
        self.remesh_action.setEnabled(False)
        self.toolbar.addSeparator()

    def setGeometry(self, geometry):
        super(EwaldCorrected, self).setGeometry(geometry)
        if geometry:
            self.cake_action.setEnabled(True)
            self.remesh_action.setEnabled(True)

    def setDisplayMode(self, mode):
        self.displaymode = mode
        if hasattr(self, "drawCenter"):
            self.drawCenter()
        self.setTransform()

    def process(self, image):
        if self.displaymode == DisplayMode.remesh:
            image, q_x, q_z = remesh(image, self._geometry, reflection=False, alphai=1)
        return image

    def transform(self, img=None):
        if not self._geometry or not self.displaymode == DisplayMode.remesh:
            return super(EwaldCorrected, self).transform(img)  # Do pixel space transform when not calibrated

        while len(img.shape) > 2:
            img = img[0]

        img, q_x, q_z = remesh(np.asarray(img), self._geometry,
                               reflection=(self.geometry_mode or 'transission' != 'transmission'),
                               alphai=self.incidence_angle)

        # Build Quads
        shape = img.shape
        a = shape[-2] - 1, 0  # bottom-left
        b = shape[-2] - 1, shape[-1] - 1  # bottom-right
        c = 0, shape[-1] - 1  # top-right
        d = 0, 0  # top-left

        quad1 = QPolygonF()
        quad2 = QPolygonF()
        for p, q in zip([a, b, c, d], [d, c, b, a]):  # the zip does the flip :P
            quad1.append(QPointF(*p[::-1]))
            quad2.append(QPointF(q_x[q], q_z[q]))

        transform = QTransform()
        QTransform.quadToQuad(quad1, quad2, transform)

        for item in self.view.items:
            if isinstance(item, ImageItem):
                item.setTransform(transform)
        self._transform = transform

        return self._transform

    def setImage(self, img, *args, geometry=None, geometry_mode=None, incidence_angle=None, **kwargs):
        if geometry_mode:
            self.geometry_mode = geometry_mode

        if incidence_angle is not None:
            self.incidence_angle = incidence_angle

        if geometry:
            self.setGeometry(geometry)

        if img is None:
            return

        if self._geometry:
            transform = self.transform(img)
            super(EwaldCorrected, self).setImage(img, *args, transform=transform, **kwargs)

        else:
            super(EwaldCorrected, self).setImage(img, *args, **kwargs)

    def updateAxes(self):
        if self.displaymode == DisplayMode.remesh:
            self.axesItem.setLabel("bottom", "q<sub>x</sub> (Å⁻¹)")  # , units='s')
            self.axesItem.setLabel("left", "q<sub>z</sub> (Å⁻¹)")
        else:
            super(EwaldCorrected, self).updateAxes()


class ROICreator(ToolbarLayout):
    """Implements a combo-box widget in the toolbar to select and create ROIs.

    Clicking on the combo-box will show all available ROIs;
    clicking on an ROI will generate the ROI intent and reset the combo-box back to its placeholder text.
    """
    def __init__(self, *args, **kwargs):
        super(ROICreator, self).__init__(*args, **kwargs)
        self.combobox = QComboBox()
        self.combobox.setPlaceholderText("Create ROI...")

        def get_icon(static_path: str):
            return QIcon(QPixmap(str((path(static_path))))) or QIcon()

        # Add roi options
        self.combobox.addItem(get_icon("icons/roi_arc.png"),
                              "Arc ROI",
                              partial(self._create_roi_action, self._create_arc_roi))
        self.combobox.addItem(get_icon("icons/roi_segmented_arc.png"),
                              "Segmented Arc ROI",
                              partial(self._create_roi_action, self._create_segmented_arc_roi))
        self.combobox.addItem(get_icon("icons/roi_rect.png"),
                              "Rectangle ROI",
                              partial(self._create_roi_action, self._create_rect_roi))
        self.combobox.addItem(get_icon("icons/roi_rect_segmented.png"),
                              "Segmented Rectangle ROI",
                              partial(self._create_roi_action, self._create_segmented_rect_roi))

        self.combobox.activated.connect(self._roi_activated)
        self.toolbar.addWidget(self.combobox)

    def _bounding_rect(self):
        rect = QRectF(self.imageItem.boundingRect())
        rect.setSize(rect.size() / 2)
        rect.moveCenter(self.imageItem.boundingRect().center())
        return rect

    def _create_arc_roi(self):
        c = (0.0, 0.0)
        r = min(*self.image.shape[-2:]) / 3
        if self._geometry is not None:
            fit = self._geometry.getFit2D()
            c = (fit['centerX'], fit['centerY'])
        return ArcROI(pos=c, radius=r, removable=False, movable=(self._geometry is None))

    def _create_segmented_arc_roi(self):
        # FIXME: code duplication
        c = (0.0, 0.0)
        r = min(*self.image.shape[-2:]) / 3
        if self._geometry is not None:
            fit = self._geometry.getFit2D()
            c = (fit['centerX'], fit['centerY'])
        return SegmentedArcROI(pos=c, radius=r, removable=False, movable=(self._geometry is None))

    def _create_rect_roi(self):
        rect = self._bounding_rect()
        return BetterRectROI(rect.topLeft(), rect.size(), removable=False)

    def _create_segmented_rect_roi(self):
        rect = self._bounding_rect()
        return SegmentedRectROI(rect.topLeft(), rect.size(), removable=False)

    def _create_roi_action(self, roi_creator):
        roi_action = ROIAction(roi_creator())
        print(f"ROI: {roi_action.roi}")
        self.parent().sigInteractiveAction.emit(roi_action, self.parent())

    def _roi_activated(self, index: int):
        # Ignore invalid index
        if index == -1:
            return

        self.combobox.itemData(index, Qt.UserRole)()
        self.combobox.setCurrentIndex(-1)


# class RectROIAction(BetterLayout):
#     def __init__(self, *args, **kwargs):
#         super(RectROIAction, self).__init__(*args, **kwargs)
#
#         self.button = QPushButton("Rectangle ROI")
#         self.button.clicked.connect(self._add_roi_action)
#         self.ui.right_layout.addWidget(self.button)
#
#     def _add_roi_action(self, _):
#         rect = QRectF(self.imageItem.boundingRect())
#         rect.setSize(rect.size()/2)
#         rect.moveCenter(self.imageItem.boundingRect().center())
#
#         roi_action = ROIAction(BetterRectROI(rect.topLeft(), rect.size()))
#         # parent is the XicamIntentCanvas
#         self.parent().sigInteractiveAction.emit(roi_action, self.parent())
#         # FIXME: removing ROIs
#         # self.button.setEnabled(False)


@live_plugin("ImageMixinPlugin")
class AxesLabels(ImageView):
    """Mixin for custom axes labels on an image view.

    This reserves usage of the kwarg "labels".
    """
    def __init__(self, *args, labels=None, **kwargs):
        if "view" in kwargs:
            raise ValueError("view cannot be passed as a kwarg")
        view = None
        if labels:
            view = pg.PlotItem()
            for axis, text in labels.items():
                view.setLabel(axis=axis, text=text)
        kwargs["view"] = view
        super(AxesLabels, self).__init__(*args, **kwargs)


if __name__ == "__main__":
    from qtpy.QtWidgets import QApplication

    qapp = QApplication([])

    # cls = type('Blend', (StreamSelector, FieldSelector), {})
    cls = type('Blend', (ToolbarLayout,), {})
    tb = QToolBar()
    tb.addAction("BLAH")
    w = cls(toolbar=tb)

    cls = type('Blend', (PixelCoordinates,), {})
    w = cls()
    w.setImage(np.random.rand(10, 10))
    w.show()

    qapp.exec_()
