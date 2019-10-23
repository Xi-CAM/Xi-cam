from pyqtgraph import ROI, PolyLineROI, Point
from pyqtgraph.graphicsItems.ROI import Handle
from qtpy.QtCore import QRectF, QPointF, Qt
from qtpy.QtGui import QPen, QColor, QPainter, QPainterPath, QVector2D, QTransform, QBrush
import numpy as np


# MIXIN!~
# Now with 100% more ROI!
class BetterROI(ROI):
    roi_count = 0
    index = None

    def __new__(cls, *args, **kwargs):
        BetterROI.roi_count += 1
        instance = ROI.__new__(cls, *args, **kwargs)
        instance.index = cls.roi_count
        return instance

    def __init__(self, *args, **kwargs):
        super(BetterROI, self).__init__(*args, **kwargs)
        self._restyle()

    def _restyle(self):
        self.currentPen.setWidth(2)

        for handledict in self.handles:  # type: dict
            handle = handledict["item"]  # type: Handle
            handle.radius = handle.radius * 2
            handle.pen.setWidth(2)
            handle.buildPath()


class BetterPolyLineROI(BetterROI, PolyLineROI):
    def __repr__(self):
        return f"ROI #{self.index}"
      

class QCircRectF(QRectF):
    def __init__(self, center=(0., 0.), radius=1., rect=None):
        self._scale = 1.
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
        return (self.right() - self.left()) * .5

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
        super(ArcROI, self).__init__(r.center, radius, removable=True, **kwargs)
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
        self.innerradius = .5 * radius
        self.outerradius = radius
        self.thetawidth = 120.

        self.innerhandle = self.addFreeHandle([0., self.innerradius / self.outerradius], [0, 0])
        self.outerhandle = self.addFreeHandle([0., 1], [0, 0])
        self.widthhandle = self.addFreeHandle(np.array([-.433 * 2, .25 * 2]))

        self.path = None
        self._restyle()

    def boundingRect(self):
        size = self.outerradius
        return QRectF(-size, -size, size * 2, size * 2).normalized()

    def movePoint(self, handle, pos, modifiers=Qt.KeyboardModifier(), finish=True, coords='parent'):
        super(ArcROI, self).movePoint(handle, pos, modifiers, finish, coords)

        # Set internal parameters
        if handle in [self.innerhandle, self.outerhandle]:
            self.innerradius = self.innerhandle.pos().length()
            self.outerradius = self.outerhandle.pos().length()

        elif handle is self.widthhandle:
            self.thetawidth = 2 * self.widthhandle.pos().angle(self.innerhandle.pos())

    def paint(self, p, opt, widget):

        # Enforce constraints on handles
        r2 = self.outerhandle.pos().norm()
        l = min(self.outerhandle.pos().length(), self.innerhandle.pos().length())
        self.innerhandle.setPos(
            r2 * l)  # constrain innerhandle to be parallel to outerhandle, and shorter than outerhandle
        widthangle = np.radians(self.thetawidth / 2 + self.outerhandle.pos().angle(Point(1, 0)))
        # constrain widthhandle to be counter-clockwise from innerhandle
        widthv = Point(np.cos(widthangle), np.sin(widthangle)) if self.thetawidth > 0 else self.innerhandle.pos().norm()
        # constrain widthhandle to half way between inner and outerhandles
        self.widthhandle.setPos(widthv * (self.innerhandle.pos() + self.outerhandle.pos()).length() / 2)

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

        p.drawLine(QPointF(0., 0.), self.widthhandle.pos().norm() / 2)
        r1v = self.innerhandle.pos().norm()
        p.drawLine(QPointF(0., 0.),
                   (-1. * self.widthhandle.pos() + 2 * self.widthhandle.pos().dot(r1v) * r1v).norm() / 2)
        pen.setStyle(Qt.SolidLine)

        if self.innerradius < self.outerradius and self.thetawidth > 0:
            path = QPainterPath()
            path.moveTo((-1. * self.widthhandle.pos() + 2 * self.widthhandle.pos().dot(r1v) * r1v).norm() / 2)
            path.arcTo(r, -startangle, -self.thetawidth)  # inside
            path.lineTo(self.widthhandle.pos().norm() / 2)  # ? side
            path.arcTo(QCircRectF(radius=0.5), -endangle, self.thetawidth)  # outside
            path.lineTo((-1. * self.widthhandle.pos() + 2 * self.widthhandle.pos().dot(r1v) * r1v).norm() / 2)
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
            lambda x, y: (self.innerhandle.pos().length() < (
                    (x - self.center[0]) ** 2. + (y - self.center[1]) ** 2.) ** .5) &
                         (((x - self.center[0]) ** 2. + (
                                 y - self.center[1]) ** 2.) ** .5 < self.outerhandle.pos().length()) &
                         ((np.degrees(np.arctan2(y - self.center[1],
                                                 x - self.center[0])) - startangle) % 360 > 0) &
                         ((np.degrees(np.arctan2(y - self.center[1],
                                                 x - self.center[0])) - startangle) % 360 < self.thetawidth)
            , (w, h))

        return arr * mask

    def shape(self):
        # (used for hitbox for menu)

        centerangle = self.innerhandle.pos().angle(Point(1, 0))
        startangle = centerangle - self.thetawidth / 2
        endangle = centerangle + self.thetawidth / 2
        r1v = self.innerhandle.pos().norm()

        # Draw out the path in external space
        path = QPainterPath()
        path.moveTo(-1. * self.widthhandle.pos() + 2 * self.widthhandle.pos().dot(r1v) * r1v)
        path.arcTo(QCircRectF(radius=self.innerradius), -startangle, -self.thetawidth)  # inside
        path.lineTo(self.widthhandle.pos())  # ? side
        path.arcTo(QCircRectF(radius=self.outerradius), -endangle, self.thetawidth)  # outside
        path.lineTo(-1. * self.widthhandle.pos() + 2 * self.widthhandle.pos().dot(r1v) * r1v)
        return path


if __name__ == '__main__':
    from qtpy.QtWidgets import QApplication

    qapp = QApplication([])
    import pyqtgraph as pg

    imageview = pg.ImageView()
    imageview.view.invertY(False)
    data = np.random.random((10, 10))
    imageview.setImage(data)

    roi = ArcROI(center=(5, 5), radius=5)
    imageview.view.addItem(roi)

    imageview2 = pg.ImageView()
    imageview2.view.invertY(False)


    def showroi(*_, **__):
        imageview2.setImage(roi.getArrayRegion(data))


    roi.sigRegionChanged.connect(showroi)

    imageview.show()
    imageview2.show()
    qapp.exec_()
