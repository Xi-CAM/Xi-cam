import weakref
from pyqtgraph import ROI, PolyLineROI, Point
from pyqtgraph.graphicsItems.ROI import Handle, RectROI, LineROI
from qtpy.QtCore import QRectF, QPointF, Qt, Signal, QSize
from qtpy.QtGui import QColor, QPainter, QPainterPath, QBrush, QPainterPathStroker, QCursor
from qtpy.QtWidgets import QAction, QVBoxLayout, QWidget, QMenu
import numpy as np
from itertools import count
from xicam.plugins import OperationPlugin

from pyqtgraph.parametertree import Parameter, parameterTypes, ParameterTree
import pyqtgraph as pg

from xicam.plugins.operationplugin import operation, output_names


class ROIOperation(OperationPlugin):
    """Single point of entry for one or more ROIs, generates a label array."""
    name = 'ROI'
    output_names = ('roi', 'labels')
    input_names = ('images', 'image_item', 'rois')

    def __init__(self, *rois: ROI):
        super(ROIOperation, self).__init__()
        self._param = None  # type: Parameter
        self.name = "ROI" #f"ROI #{self.ROI.index}"

    def _func(self, images, image_item=None, rois=None):
        # Create zeros label array to insert new labels into (if multiple ROIs)
        label_array = np.zeros(images[0].shape)
        roi_masks = []
        for roi in rois:
            # TODO: Should label array be astype(np.int) (instead of float)?
            label = roi.getLabelArray(images, image_item)
            # Store the boolean mask of each label array
            roi_mask = label.astype(np.bool)
            roi_masks.append(roi_mask)
            # Grab the current label array maximum value (so we can increment multiple labels accordingly)
            label_array_max = label_array.max()
            label = np.where(label > 0, label + label_array_max, label)
            # For single roi, our max will be 0 (since label_array is just np.zeros so far, hasn't been modified)
            if label_array_max == 0:
                label_array = label
                print(f"{label_array_max + 1}: {(label_array == 1).sum()}")
                print()
            else:
                # FIXME right now, if labels overlap, label integers are being added together (into a new label value)
                # Adjust any currently non-masked areas with the new label
                label_array = np.where(label_array == 0, label, label_array)
                print(f"{1}: {(label_array == 1).sum()}")
                print(f"{2}: {(label_array == 2).sum()}")
                print()
                #
                label_array = np.where(label_array > 0,
                                       np.where(label > 0, label, label_array),
                                       label_array)
                # label_array = np.where(label_array > 0,
                #                        label or label_array,
                #                        label_array)
                print(f"1: {(label_array == 1).sum()}")
                print(f"2: {(label_array == 2).sum()}")
                print()


        return roi_masks, label_array

    # TODO: might need this for adjusting roi's manually
    # @property
    # def parameter(self):
    #     if not self._param:
    #         self._param = self.roi.parameter()
    #     return self._param


class WorkflowableROI(ROI):
    # FIXME: do we still want this for our (e.g.) CorrelationStage process_actions???
    def __init__(self, *args, **kwargs):
        super(WorkflowableROI, self).__init__(*args, **kwargs)
        self.operation = ROIOperation(self)
        self._param = None

    def parameter(self) -> Parameter:
        raise NotImplementedError

    def getMenu(self):
        if self.menu is None:
            self.menu = QMenu()
            self.menu.setTitle("ROI")
            if self.removable:  # FIXME: if the removable attr is changed, the menu will not react and remAct won't show
                remAct = QAction("Remove ROI", self.menu)
                remAct.triggered.connect(self.removeClicked)
                self.menu.addAction(remAct)
                self.menu.remAct = remAct
            editAct = QAction("Edit ROI", self.menu)
            editAct.triggered.connect(self.edit_parameters)
            self.menu.addAction(editAct)
            self.menu.editAct = editAct
        self.menu.setEnabled(True)
        return self.menu

    def contextMenuEnabled(self):
        return True

    def edit_parameters(self):
        class DefocusParameterTree(QWidget):
            def __init__(self, *args, **kwargs):
                super(DefocusParameterTree, self).__init__(*args, **kwargs)
                self.setLayout(QVBoxLayout())
                self.parameter_tree = ParameterTree()
                self.layout().addWidget(self.parameter_tree)
                self.layout().setContentsMargins(0, 0, 0, 0)

            def setParameters(self, *args, **kwargs):
                self.parameter_tree.setParameters(*args, **kwargs)

        # self.parameter_tree = DefocusParameterTree()
        self.parameter_tree = DefocusParameterTree()
        self.parameter_tree.setParameters(self.parameter())
        self.parameter_tree.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        # self.parameter_tree = QLabel('blah')
        self.parameter_tree.show()
        self.parameter_tree.activateWindow()
        self.parameter_tree.raise_()
        self.parameter_tree.move(QCursor().pos())
        self.parameter_tree.setFocus(Qt.PopupFocusReason)
        self.parameter_tree.resize(QSize(300, 400))


# MIXIN!~
# Now with 100% more ROI!
class BetterROI(WorkflowableROI):
    roi_count = count(1)
    index = None

    def __init__(self, *args, **kwargs):
        super(BetterROI, self).__init__(*args, **kwargs)
        # # BetterROI removable by default
        # super(BetterROI, self).__init__(*args, removable=removable, **kwargs)
        self.index = next(self.roi_count)
        self._restyle()

        # Remove the roi from the view when requested to be removed
        self.sigRemoveRequested.connect(lambda roi: self._viewBox().removeItem(roi))

        self._name = "ROI"

    def __str__(self):
        return f"ROI #{self.index} ({self._name})"

    def _restyle(self):
        self.currentPen.setWidth(2)

        for handledict in self.handles:  # type: dict
            handle = handledict["item"]  # type: Handle
            handle.radius = handle.radius * 2
            handle.pen.setWidth(2)
            handle.buildPath()

    def hoverEvent(self, ev):
        hover = False
        if not ev.isExit():
            if ev.acceptDrags(Qt.LeftButton):
                hover = True
            for btn in [Qt.LeftButton, Qt.RightButton, Qt.MidButton]:
                if int(self.acceptedMouseButtons() & btn) > 0 and ev.acceptClicks(btn):
                    hover = True

        if hover:
            self.currentPen = pg.mkPen(255, 255, 0, width=2)
        else:
            self.currentPen = self.pen
        self.update()

    def valueChanged(self, sender, changes):
        for change in changes:
            setattr(self, change[0].name(), change[2])
        self.stateChanged()


class BetterPolyLineROI(BetterROI, PolyLineROI):
    def __repr__(self):
        return f"ROI #{self.index}"


class QCircRectF(QRectF):
    def __init__(self, center=(0.0, 0.0), radius=1.0, rect=None):
        self._scale = 1.0
        if rect is not None:
            self.center = rect.center()
            super(QCircRectF, self).__init__(rect)
        else:
            self.center = QPointF(*center)

            left = self.center.x() - radius
            top = self.center.y() - radius
            bottom = self.center.y() + radius
            right = self.center.x() + radius

            super(QCircRectF, self).__init__(QPointF(left, top), QPointF(right, bottom))

    @property
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, value):
        self._scale = value
        self.radius *= value
        self.setLeft(self.center.x() - self._radius)
        self.setTop(self.center.y() - self._radius)
        self.setBottom(self.center.y() + self._radius)
        self.setRight(self.center.x() + self._radius)

    @property
    def radius(self):
        return (self.right() - self.left()) * 0.5

    @radius.setter
    def radius(self, radius):

        self.setLeft(self.center.x() - radius)
        self.setTop(self.center.y() - radius)
        self.setBottom(self.center.y() + radius)
        self.setRight(self.center.x() + radius)


class BetterCrosshairROI(BetterROI):
    sigMoved = Signal(object)
    """A crosshair ROI whose position is at the center of the crosshairs. By default, it is scalable, rotatable and translatable."""

    def __init__(self, pos=None, size=None, parent=None, **kwargs):
        assert parent

        if size == None:
            size = [0, 0]
        if pos == None:
            pos = [0, 0]

        self._shape = None
        linepen = pg.mkPen("#FFA500", width=2)
        self._vline = pg.InfiniteLine((0, 0), angle=90, movable=False, pen=linepen)
        self._hline = pg.InfiniteLine((0, 0), angle=0, movable=False, pen=linepen)

        super(BetterCrosshairROI, self).__init__(pos, size, parent=parent, **kwargs)
        parent.addItem(self)

        self.sigRegionChanged.connect(self.invalidate)
        self.addTranslateHandle(Point(0, 0))
        self.aspectLocked = True

        parent.addItem(self._vline)
        parent.getViewBox().addItem(self._hline)

        self._name = "Crosshair ROI"

    def translate(self, *args, **kwargs):
        super(BetterCrosshairROI, self).translate(*args, **kwargs)
        self.sigMoved.emit(self.pos())

    def stateChanged(self, finish=True):
        super(BetterCrosshairROI, self).stateChanged()
        self._hline.setPos(self.pos().y())
        self._vline.setPos(self.pos().x())

    def invalidate(self):
        self._shape = None
        self.prepareGeometryChange()

    def boundingRect(self):
        return self.shape().boundingRect()

    def shape(self):
        if self._shape is None:
            radius = self.getState()['size'][1]
            p = QPainterPath()
            p.moveTo(Point(0, -radius))
            p.lineTo(Point(0, radius))
            p.moveTo(Point(-radius, 0))
            p.lineTo(Point(radius, 0))
            p = self.mapToDevice(p)
            stroker = QPainterPathStroker()
            stroker.setWidth(10)
            outline = stroker.createStroke(p)
            self._shape = self.mapFromDevice(outline)

        return self._shape


class ArcROI(BetterROI):
    """
    A washer-wedge-shaped ROI for selecting q-ranges

    """

    def __init__(self, pos, radius, **kwargs):
        # QtGui.QGraphicsRectItem.__init__(self, 0, 0, size[0], size[1])
        r = QCircRectF(pos, radius)
        super(ArcROI, self).__init__(r.center, radius, **kwargs)
        # self.addRotateHandle([1.0, 0.5], [0.5, 0.5])
        # self.addScaleHandle([0.5*2.**-0.5 + 0.5, 0.5*2.**-0.5 + 0.5], [0.5, 0.5])

        self.startangle = 30
        self.arclength = 120
        self.radius_name = 'Radius'
        self.radius_units = 'px'

        self.aspectLocked = True

        # only these values are in external space, others are internal (-.5,.5)
        self.innerradius = 0.5 * radius
        self.outerradius = radius
        self.thetawidth = 120.0
        self.thetacenter = 90.0

        self.innerhandle = self.addFreeHandle([0.0, self.innerradius / self.outerradius], [0, 0])
        self.outerhandle = self.addFreeHandle([0.0, 1], [0, 0])
        self.widthhandle = self.addFreeHandle(np.array([-0.433 * 2, 0.25 * 2]))

        self.path = None
        self._param = None  # type: Parameter
        self._restyle()

        self._name = "Arc ROI"

    def boundingRect(self):
        size = self.outerradius
        return QRectF(-size, -size, size * 2, size * 2).normalized()

    def movePoint(self, handle, pos, modifiers=Qt.KeyboardModifier(), finish=True, coords="parent"):
        super(ArcROI, self).movePoint(handle, pos, modifiers, finish, coords)

        self._update_internal_parameters(handle)

    def _update_internal_parameters(self, handle=None):
        # Set internal parameters
        if handle is self.innerhandle:
            self.innerradius = min(self.innerhandle.pos().length(), self.outerhandle.pos().length())

        elif handle is self.outerhandle:
            self.innerradius = self.innerhandle.pos().length()
            self.outerradius = self.outerhandle.pos().length()

        if handle is self.outerhandle:
            self.thetacenter = self.outerhandle.pos().angle(Point(1, 0))

        elif handle is self.widthhandle:
            self.thetawidth = max(2 * self.widthhandle.pos().angle(self.innerhandle.pos()), 0)

        self.handleChanged()

    def paint(self, p, opt, widget):

        # Enforce constraints on handles
        r2 = Point(np.cos(np.radians(self.thetacenter)),
                   np.sin(np.radians(self.thetacenter)))  # chi center direction vector
        # constrain innerhandle to be parallel to outerhandle, and shorter than outerhandle
        self.innerhandle.setPos(r2 * self.innerradius)
        if self.innerhandle.pos().length() > self.outerhandle.pos().length():
            self.innerhandle.setPos(r2 * self.outerradius)
        # constrain widthhandle to be counter-clockwise from innerhandle
        widthangle = np.radians(self.thetawidth / 2 + self.thetacenter)
        widthv = Point(np.cos(widthangle), np.sin(widthangle)) if self.thetawidth > 0 else r2
        # constrain widthhandle to half way between inner and outerhandles
        self.widthhandle.setPos(widthv * (self.innerradius + self.outerradius) / 2)
        # constrain handles to base values
        self.outerhandle.setPos(r2 * self.outerradius)

        pen = self.currentPen
        pen.setColor(QColor(0, 255, 255))
        pen.setStyle(Qt.SolidLine)

        p.setPen(pen)

        r = self.boundingRect()
        # p.drawRect(r)
        p.setRenderHint(QPainter.Antialiasing)

        p.scale(r.width(), r.height())  # workaround for GL bug

        centerangle = self.innerhandle.pos().angle(Point(1, 0))
        startangle = centerangle - self.thetawidth / 2
        endangle = centerangle + self.thetawidth / 2

        r = QCircRectF(radius=0.5)
        if self.innerradius < self.outerradius and self.thetawidth > 0:
            p.drawArc(r, -startangle * 16, -self.thetawidth * 16)

        radius = self.innerradius / self.outerradius / 2
        r = QCircRectF()
        r.radius = radius

        if self.innerradius < self.outerradius and self.thetawidth > 0:
            p.drawArc(r, -startangle * 16, -self.thetawidth * 16)

        pen.setStyle(Qt.DashLine)
        p.setPen(pen)

        p.drawLine(QPointF(0.0, 0.0), self.widthhandle.pos().norm() / 2)
        r1v = self.innerhandle.pos().norm()
        p.drawLine(QPointF(0.0, 0.0), (-1.0 * self.widthhandle.pos() + 2 * self.widthhandle.pos().dot(r1v) * r1v).norm() / 2)
        pen.setStyle(Qt.SolidLine)

        if self.innerradius < self.outerradius and self.thetawidth > 0:
            path = QPainterPath()
            path.moveTo((-1.0 * self.widthhandle.pos() + 2 * self.widthhandle.pos().dot(r1v) * r1v).norm() / 2)
            path.arcTo(r, -startangle, -self.thetawidth)  # inside
            path.lineTo(self.widthhandle.pos().norm() / 2)  # ? side
            path.arcTo(QCircRectF(radius=0.5), -endangle, self.thetawidth)  # outside
            path.lineTo((-1.0 * self.widthhandle.pos() + 2 * self.widthhandle.pos().dot(r1v) * r1v).norm() / 2)
            self.path = path
            p.fillPath(path, QBrush(QColor(0, 255, 255, 20)))

    def getArrayRegion(self, arr, img=None):
        """
        Return the result of ROI.getArrayRegion() masked by the arc shape
        of the ROI. Regions outside the arc are set to 0.
        """
        w = arr.shape[-2]
        h = arr.shape[-1]

        centerangle = self.outerhandle.pos().angle(Point(1, 0))
        startangle = centerangle - self.thetawidth / 2

        # generate an ellipsoidal mask
        mask = np.fromfunction(
            lambda y, x: (
                                 self.innerhandle.pos().length() < (
                                     (x - self.pos().y()) ** 2.0 + (y - self.pos().x()) ** 2.0) ** 0.5
                         )
                         & (((x - self.pos().y()) ** 2.0 + (
                        y - self.pos().x()) ** 2.0) ** 0.5 < self.outerhandle.pos().length())
                         & ((np.degrees(np.arctan2(y - self.pos().x(), x - self.pos().y())) - startangle) % 360 > 0)
                         & ((np.degrees(
                np.arctan2(y - self.pos().x(), x - self.pos().y())) - startangle) % 360 < self.thetawidth),
            (w, h),
        )

        return arr * mask

    def getLabelArray(self, arr, img: pg.ImageItem = None):
        """Return a label array (ones and zeros) for the masked array region defined by the ROI."""
        masked_arr = self.getArrayRegion(arr, img)
        return (masked_arr != 0).astype(np.uint8)

    def shape(self):
        # (used for hitbox for menu)

        centerangle = self.innerhandle.pos().angle(Point(1, 0))
        startangle = centerangle - self.thetawidth / 2
        endangle = centerangle + self.thetawidth / 2
        r1v = self.innerhandle.pos().norm()

        # Draw out the path in external space
        path = QPainterPath()
        path.moveTo(-1.0 * self.widthhandle.pos() + 2 * self.widthhandle.pos().dot(r1v) * r1v)
        path.arcTo(QCircRectF(radius=self.innerradius), -startangle, -self.thetawidth)  # inside
        path.lineTo(self.widthhandle.pos())  # ? side
        path.arcTo(QCircRectF(radius=self.outerradius), -endangle, self.thetawidth)  # outside
        path.lineTo(-1.0 * self.widthhandle.pos() + 2 * self.widthhandle.pos().dot(r1v) * r1v)
        return path

    def parameter(self):
        if not self._param:
            self._param = parameterTypes.GroupParameter(
                name="Arc ROI",
                children=[
                    parameterTypes.SimpleParameter(
                        title=f"{self.radius_name} Minimum", name="innerradius", value=self.innerradius, type="float",
                        units=self.radius_units, min=0
                        # "Å⁻¹"
                    ),
                    parameterTypes.SimpleParameter(
                        title=f"{self.radius_name} Maximum", name="outerradius", value=self.outerradius, type="float",
                        units=self.radius_units, min=0
                    ),
                    parameterTypes.SimpleParameter(
                        title="χ Width", name="thetawidth", value=self.thetawidth, type="float", units="°"
                    ),
                    parameterTypes.SimpleParameter(
                        title="χ Center", name="thetacenter", value=self.thetacenter, type="float", siSuffix="°"
                    ),
                ],
            )

            self._param.sigTreeStateChanged.connect(self.valueChanged)

        return self._param

    def handleChanged(self):
        self.parameter().child("innerradius").setValue(self.innerradius)
        self.parameter().child("outerradius").setValue(self.outerradius)
        self.parameter().child("thetawidth").setValue(self.thetawidth)
        self.parameter().child("thetacenter").setValue(self.thetacenter)


class ArcQRoi(ArcROI):
    ...


class SegmentedArcROI(ArcROI):
    """
    A washer-wedge-shaped ROI for selecting q-ranges

    """

    def __init__(self, pos, radius, **kwargs):
        # QtGui.QGraphicsRectItem.__init__(self, 0, 0, size[0], size[1])
        self.segments_radial = 3
        self.segments_angular = 3
        super(SegmentedArcROI, self).__init__(pos, radius, **kwargs)

        self._name = "Segmented Arc ROI"

    def paint(self, p, opt, widget):
        super(SegmentedArcROI, self).paint(p, opt, widget)

        pen = self.currentPen
        # pen.setColor(QColor(255, 0, 255))
        pen.setStyle(Qt.DashLine)
        p.setPen(pen)

        centerangle = self.innerhandle.pos().angle(Point(1, 0))
        startangle = centerangle - self.thetawidth / 2
        endangle = centerangle + self.thetawidth / 2
        segment_angles = np.linspace(startangle, endangle, self.segments_angular, endpoint=False)[1:]
        segment_radii = np.linspace(self.innerradius, self.outerradius, self.segments_radial, endpoint=False)[1:]

        r = QCircRectF(radius=0.5)
        radius = self.innerradius / self.outerradius / 2
        r = QCircRectF()
        r.radius = radius

        # draw segments
        for segment_radius in segment_radii:
            r.radius = segment_radius / self.outerradius / 2
            # p.drawRect(r)
            p.drawArc(r, -startangle * 16, -self.thetawidth * 16)

        if self.innerradius < self.outerradius:
            for segment_angle in segment_angles:
                segment_vector = QPointF(np.cos(np.radians(segment_angle)), np.sin(np.radians(segment_angle)))

                p.drawLine(segment_vector * self.innerradius / self.outerradius / 2, segment_vector / 2)

    def getLabelArray(self, arr, img: pg.ImageItem = None):
        labels = np.zeros(arr.shape[-2:])

        centerangle = -self.outerhandle.pos().angle(Point(0, 1))
        startangle = centerangle - self.thetawidth / 2
        endangle = centerangle + self.thetawidth / 2
        radii = np.linspace(self.innerradius, self.outerradius, self.segments_radial + 1, endpoint=True)
        angles = np.linspace(startangle, endangle, self.segments_angular + 1, endpoint=True)

        start_radii = radii[:-1]
        end_radii = radii[1:]
        start_angles = angles[:-1]
        end_angles = angles[1:]

        for i, (start_radius, end_radius) in enumerate(zip(start_radii, end_radii)):
            for j, (start_angle, end_angle) in enumerate(zip(start_angles, end_angles)):
                # generate an ellipsoidal mask
                mask = np.fromfunction(
                    lambda x, y: (start_radius <= ((x - self.pos().y()) ** 2.0 + (y - self.pos().x()) ** 2.0) ** 0.5)
                                 & (((x - self.pos().y()) ** 2.0 + (y - self.pos().x()) ** 2.0) ** 0.5 <= end_radius)
                                 & ((np.degrees(
                        np.arctan2(y - self.pos().x(), x - self.pos().y())) - start_angle) % 360 >= 0)
                                 & ((np.degrees(np.arctan2(y - self.pos().x(),
                                                           x - self.pos().y())) - start_angle) % 360 <= end_angle - start_angle),
                    arr.shape[-2:], )
                labels[mask] = i * self.segments_radial + j + 1

        return labels

    def parameter(self):
        if not self._param:
            self._param = parameterTypes.GroupParameter(
                name="Segmented Arc ROI",
                children=[
                    parameterTypes.SimpleParameter(
                        title="χ Segments", name="segments_angular", value=self.segments_angular, type="int", min=1
                    ),
                    parameterTypes.SimpleParameter(
                        title=f"{self.radius_name} segments", name="segments_radial", value=self.segments_radial,
                        type="int", min=1
                    ),
                    parameterTypes.SimpleParameter(
                        title=f"{self.radius_name} Minimum", name="innerradius", value=self.innerradius, type="float",
                        units=self.radius_units, min=0
                    ),
                    parameterTypes.SimpleParameter(
                        title=f"{self.radius_name} Maximum", name="outerradius", value=self.outerradius, type="float",
                        units=self.radius_units, min=0
                    ),
                    parameterTypes.SimpleParameter(
                        title="χ Width", name="thetawidth", value=self.thetawidth, type="float", units="°"
                    ),
                    parameterTypes.SimpleParameter(
                        title="χ Center", name="thetacenter", value=self.thetacenter, type="float", siSuffix="°"
                    ),

                ],
            )

            self._param.sigTreeStateChanged.connect(self.valueChanged)

        return self._param


class BetterRectROI(BetterROI, RectROI):
    def __init__(self, *args, pen=pg.mkPen(QColor(0, 255, 255)), **kwargs):
        super(BetterRectROI, self).__init__(*args, pen=pen, **kwargs)
        self.handle = self.handles[0]

        self._name = "Rectangle ROI"

    def __reduce__(self):
        # FIXME: very simple reduce for allowing copy (to help with weakref management)
        return self.__class__, (self.pos(), self.size())

    def movePoint(self, handle, pos, modifiers=Qt.KeyboardModifier(), finish=True, coords="parent"):
        super(BetterRectROI, self).movePoint(handle, pos, modifiers, finish, coords)

        self.width = self.handle["pos"].x() * self.size().x()
        self.height = self.handle["pos"].y() * self.size().y()

        self.handleChanged()

    def parameter(self) -> Parameter:
        if not self._param:
            self._param = parameterTypes.GroupParameter(
                name="Rectangular ROI",
                children=[
                    parameterTypes.SimpleParameter(title="Width", name="width", value=self.width, type="float", units="px"),
                    parameterTypes.SimpleParameter(
                        title="Height", name="height", value=self.height, type="float", units="px"
                    ),
                ],
            )

            self._param.sigTreeStateChanged.connect(self.valueChanged)

        return self._param

    def handleChanged(self):
        self.parameter().child("width").setValue(self.width)
        self.parameter().child("height").setValue(self.height)

    def getLabelArray(self, arr, img: pg.ImageItem = None):
        # TODO : make more generic for all rectangle ROIs, segmented (multi-labeled) and non-segmented (single-labeled)
        dim_0, dim_1 = arr.shape[-2:]

        min_x = self.pos().x()
        min_y = self.pos().y()
        max_x = self.size().x() + min_x
        max_y = self.size().y() + min_y

        mask = np.zeros(arr.shape[-2:])

        label_mask = np.fromfunction(
            lambda y, x: (x + 0.5 > min_x) & (x + 0.5 < max_x) & (y + 0.5 > min_y) & (y + 0.5 < max_y), (dim_0, dim_1)
        )
        mask[label_mask] = 1

        # Invert y
        # FIXME -- use image transform above with passed image item
        return mask


class LineROI(BetterROI, LineROI):
    def __init__(self, *args, pen=pg.mkPen(QColor(0, 255, 255)), **kwargs):
        super(LineROI, self).__init__(*args, pen=pen, **kwargs)
        self._update_state()

        self._name = "Line ROI"

    def _update_state(self):
        self.width = self.size().y()
        self.length = self.size().x()
        self.rotation = self.angle()
        self.center_x = self.pos().x()
        self.center_y = self.pos().y()

    def movePoint(self, handle, pos, modifiers=Qt.KeyboardModifier(), finish=True, coords="parent"):
        super(LineROI, self).movePoint(handle, pos, modifiers, finish, coords)

        self._update_state()
        self.handleChanged()

    def mouseDragEvent(self, ev):
        super(LineROI, self).mouseDragEvent(ev)
        self._update_state()

    def paint(self, p, opt, widget):
        self.setSize(QPointF(self.length, self.width))
        self.setAngle(self.rotation)
        self.setPos(QPointF(self.center_x, self.center_y))
        super(LineROI, self).paint(p, opt, widget)

    def parameter(self) -> Parameter:
        if not self._param:
            self._param = parameterTypes.GroupParameter(
                name="Line ROI",
                children=[
                    parameterTypes.SimpleParameter(
                        title="Center X", name="center_x", value=self.center_x, type="float", units="px"
                    ),
                    parameterTypes.SimpleParameter(
                        title="Center Y", name="center_y", value=self.center_y, type="float", units="px"
                    ),
                    parameterTypes.SimpleParameter(
                        title="Rotation Angle", name="rotation", value=self.rotation, type="float", units="px"
                    ),
                    parameterTypes.SimpleParameter(
                        title="Length", name="length", value=self.length, type="float", units="px"
                    ),
                    parameterTypes.SimpleParameter(title="Width", name="width", value=self.width, type="float", units="px"),
                ],
            )

            self._param.sigTreeStateChanged.connect(self.valueChanged)

        return self._param

    def handleChanged(self):
        self.parameter().child("center_x").setValue(self.center_x)
        self.parameter().child("center_y").setValue(self.center_y)
        self.parameter().child("rotation").setValue(self.rotation)
        self.parameter().child("width").setValue(self.width)
        self.parameter().child("length").setValue(self.length)


class SegmentedRectROI(BetterRectROI):
    def __init__(self, *args, **kwargs):
        self.segments_h = 2
        self.segments_v = 2
        super(SegmentedRectROI, self).__init__(*args, **kwargs)

        self._name = "Segmented Rectangle ROI"

    def parameter(self) -> Parameter:
        if not self._param:
            self._param = parameterTypes.GroupParameter(
                name="Rectangular ROI",
                children=[
                    parameterTypes.SimpleParameter(title="Width", name="width", value=self.width, type="float", units="px"),
                    parameterTypes.SimpleParameter(
                        title="Height", name="height", value=self.height, type="float", units="px"
                    ),
                    parameterTypes.SimpleParameter(
                        title="Horizontal Segments", name="segments_h", value=self.segments_h, type="int"
                    ),
                    parameterTypes.SimpleParameter(
                        title="Vertical Segments", name="segments_v", value=self.segments_v, type="int"
                    ),
                ],
            )

            self._param.sigTreeStateChanged.connect(self.valueChanged)

        return self._param

    def getLabelArray(self, arr, img=None):
        """
        Return the result of ROI.getArrayRegion() masked by the arc shape
        of the ROI. Regions outside the arc are set to 0.
        """
        w, h = arr.shape

        min_x = self.pos().x()
        min_y = self.pos().y()
        max_x = self.size().x() + min_x
        max_y = self.size().y() + min_y
        segment_bin_x = (max_x - min_x) / self.segments_h
        segment_bin_y = (max_y - min_y) / self.segments_v

        mask = np.zeros_like(arr)

        for i in range(self.segments_h):
            for j in range(self.segments_v):
                # generate an square max
                label_mask = np.fromfunction(
                    lambda y, x: (x + 0.5 > min_x + i * segment_bin_x)
                                 & (x + 0.5 < min_x + (i + 1) * segment_bin_x)
                                 & (y + 0.5 > min_y + j * segment_bin_y)
                                 & (y + 0.5 < min_y + (j + 1) * segment_bin_y),
                    (w, h),
                )
                mask[label_mask] = 1 + i + j * self.segments_h

        return mask

    def paint(self, p, opt, widget):
        super(SegmentedRectROI, self).paint(p, opt, widget)

        min_x = self.pos().x()
        min_y = self.pos().y()
        max_x = self.size().x() + min_x
        max_y = self.size().y() + min_y
        segment_bin_x = (max_x - min_x) / self.segments_h
        segment_bin_y = (max_y - min_y) / self.segments_v

        self.currentPen.setStyle(Qt.DashLine)
        p.setPen(self.currentPen)

        for i in range(1, self.segments_h):
            p.drawLine(QPointF(1.0 / self.segments_h * i, 0), QPointF(1 / self.segments_h * i, 1))

        for j in range(1, self.segments_v):
            p.drawLine(QPointF(0, 1 / self.segments_v * j), QPointF(1, 1 / self.segments_v * j))

        self.currentPen.setStyle(Qt.SolidLine)


if __name__ == "__main__":
    from qtpy.QtWidgets import QApplication, QLabel, QVBoxLayout, QAbstractScrollArea

    qapp = QApplication([])
    import pyqtgraph as pg

    pg.setConfigOption('imageAxisOrder', 'row-major')
    imageview = pg.ImageView()
    data = np.random.random((100, 100))
    imageview.setImage(data)

    # roi = ArcROI(pos=(50, 50), radius=50)
    roi = BetterRectROI(pos=(0, 0), size=(10, 10))
    # roi = SegmentedArcROI(pos=(50,50), radius=50)
    # roi = BetterCrosshairROI((0, 0), parent=imageview.view)
    imageview.view.addItem(roi)

    imageview.show()

    iv2 = pg.ImageView()
    iv2.show()


    def show_labels():
        iv2.setImage(roi.getLabelArray(data, imageview.imageItem))


    roi.sigRegionChanged.connect(show_labels)
    qapp.exec_()
