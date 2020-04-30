from pyqtgraph import ROI, PolyLineROI, Point
from pyqtgraph.graphicsItems.ROI import Handle, RectROI, LineROI
from qtpy.QtCore import QRectF, QPointF, Qt
from qtpy.QtGui import QColor, QPainter, QPainterPath, QBrush
import numpy as np
from itertools import count
from xicam.plugins import OperationPlugin


from pyqtgraph.parametertree import Parameter, parameterTypes
import pyqtgraph as pg


class ROIProcessingPlugin(OperationPlugin):
    name = 'ROI'
    output_names = ('ROI', 'data')

    def __init__(self, ROI: ROI):
        super(ROIProcessingPlugin, self).__init__()
        self.ROI = ROI
        self._param = None  # type: Parameter

        self.name = f"ROI #{self.ROI.index}"

    def _func(self, data, image):
        data = self.ROI.getLabelArray(data, image)
        roi = data.astype(np.bool)
        return roi, data

    @property
    def parameter(self):
        if not self._param:
            self._param = self.ROI.parameter()
        return self._param


class WorkflowableROI(ROI):
    def __init__(self, *args, **kwargs):
        super(WorkflowableROI, self).__init__(*args, **kwargs)
        self.process = ROIProcessingPlugin(self)
        self._param = None

    def parameter(self) -> Parameter:
        raise NotImplementedError


# MIXIN!~
# Now with 100% more ROI!
class BetterROI(WorkflowableROI):
    roi_count = count(0)
    index = None

    def __init__(self, *args, removable=True, **kwargs):
        # BetterROI removable by default
        super(BetterROI, self).__init__(*args, removable=removable, **kwargs)
        self.index = next(self.roi_count)
        self._restyle()
        # Remove the roi from the view when requested to be removed
        self.sigRemoveRequested.connect(lambda roi: self._viewBox().removeItem(roi))

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


class ArcROI(BetterROI):
    """
    A washer-wedge-shaped ROI for selecting q-ranges

    """

    def __init__(self, center, radius, **kwargs):
        # QtGui.QGraphicsRectItem.__init__(self, 0, 0, size[0], size[1])
        r = QCircRectF(center, radius)
        super(ArcROI, self).__init__(r.center, radius, **kwargs)
        # self.addRotateHandle([1.0, 0.5], [0.5, 0.5])
        # self.addScaleHandle([0.5*2.**-0.5 + 0.5, 0.5*2.**-0.5 + 0.5], [0.5, 0.5])

        self.startangle = 30
        self.arclength = 120

        self.aspectLocked = True
        self.translatable = False
        self.translateSnap = False
        self.removable = True

        self.center = center

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

    def boundingRect(self):
        size = self.outerradius
        return QRectF(-size, -size, size * 2, size * 2).normalized()

    def movePoint(self, handle, pos, modifiers=Qt.KeyboardModifier(), finish=True, coords="parent"):
        super(ArcROI, self).movePoint(handle, pos, modifiers, finish, coords)

        # Set internal parameters
        if handle in [self.innerhandle, self.outerhandle]:
            self.innerradius = self.innerhandle.pos().length()
            self.outerradius = self.outerhandle.pos().length()
            self.thetacenter = self.outerhandle.pos().angle(Point(1, 0))

        elif handle is self.widthhandle:
            self.thetawidth = 2 * self.widthhandle.pos().angle(self.innerhandle.pos())

        self.handleChanged()

    def paint(self, p, opt, widget):

        # Enforce constraints on handles
        r2 = Point(np.cos(np.radians(self.thetacenter)), np.sin(np.radians(self.thetacenter)))  # chi center direction vector
        # constrain innerhandle to be parallel to outerhandle, and shorter than outerhandle
        self.innerhandle.setPos(r2 * self.innerradius)
        # constrain widthhandle to be counter-clockwise from innerhandle
        widthangle = np.radians(self.thetawidth / 2 + self.thetacenter)
        widthv = Point(np.cos(widthangle), np.sin(widthangle)) if self.thetawidth > 0 else r2
        # constrain widthhandle to half way between inner and outerhandles
        self.widthhandle.setPos(widthv * (self.innerradius + self.outerradius) / 2)
        # constrain handles to base values
        self.outerhandle.setPos(r2 * self.outerradius)

        pen = self.currentPen
        pen.setColor(QColor(0, 255, 255))

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
        w = arr.shape[0]
        h = arr.shape[1]

        centerangle = self.outerhandle.pos().angle(Point(1, 0))
        startangle = centerangle - self.thetawidth / 2

        # generate an ellipsoidal mask
        mask = np.fromfunction(
            lambda x, y: (
                self.innerhandle.pos().length() < ((x - self.center[0]) ** 2.0 + (y - self.center[1]) ** 2.0) ** 0.5
            )
            & (((x - self.center[0]) ** 2.0 + (y - self.center[1]) ** 2.0) ** 0.5 < self.outerhandle.pos().length())
            & ((np.degrees(np.arctan2(y - self.center[1], x - self.center[0])) - startangle) % 360 > 0)
            & ((np.degrees(np.arctan2(y - self.center[1], x - self.center[0])) - startangle) % 360 < self.thetawidth),
            (w, h),
        )

        return arr * mask

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
                        title="Q Minimum", name="innerradius", value=self.innerradius, type="float", units="Å⁻¹"
                    ),
                    parameterTypes.SimpleParameter(
                        title="Q Maximum", name="outerradius", value=self.outerradius, type="float", units="Å⁻¹"
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


class RectROI(BetterROI, RectROI):
    def __init__(self, *args, pen=pg.mkPen(QColor(0, 255, 255)), **kwargs):
        super(RectROI, self).__init__(*args, pen=pen, **kwargs)
        self.handle = self.handles[0]

    def movePoint(self, handle, pos, modifiers=Qt.KeyboardModifier(), finish=True, coords="parent"):
        super(RectROI, self).movePoint(handle, pos, modifiers, finish, coords)

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
        dim_0, dim_1 = arr.shape

        min_x = self.pos().x()
        min_y = self.pos().y()
        max_x = self.size().x() + min_x
        max_y = self.size().y() + min_y

        mask = np.zeros_like(arr)

        label_mask = np.fromfunction(
            lambda y, x: (x + 0.5 > min_x) & (x + 0.5 < max_x) & (y + 0.5 > min_y) & (y + 0.5 < max_y), (dim_0, dim_1)
        )
        mask[label_mask] = 1

        # Invert y
        # FIXME -- use image transform above with passed image item
        return mask[::-1, ::]


class LineROI(BetterROI, LineROI):
    def __init__(self, *args, pen=pg.mkPen(QColor(0, 255, 255)), **kwargs):
        super(LineROI, self).__init__(*args, pen=pen, **kwargs)
        self._update_state()

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


class SegmentedRectROI(RectROI):
    def __init__(self, *args, **kwargs):
        self.segments_h = 2
        self.segments_v = 2
        super(SegmentedRectROI, self).__init__(*args, **kwargs)

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
                    lambda x, y: (x + 0.5 > min_x + i * segment_bin_x)
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
    from qtpy.QtWidgets import QApplication

    qapp = QApplication([])
    import pyqtgraph as pg

    imageview = pg.ImageView()
    imageview.view.invertY(False)
    data = np.random.random((10, 10))
    imageview.setImage(data)

    # roi = ArcROI(center=(5, 5), radius=5)
    roi = SegmentedRectROI(pos=(0, 0), size=(10, 10))
    imageview.view.addItem(roi)

    imageview2 = pg.ImageView()
    imageview2.view.invertY(False)

    def showroi(*_, **__):
        imageview2.setImage(roi.getLabelArray(data, imageview.imageItem))

    roi.sigRegionChanged.connect(showroi)

    imageview.show()
    imageview2.show()
    qapp.exec_()
