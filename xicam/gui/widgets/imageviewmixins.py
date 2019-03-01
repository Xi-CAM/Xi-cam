from functools import WRAPPER_ASSIGNMENTS
from pyqtgraph import ImageView, InfiniteLine, mkPen, ScatterPlotItem, ImageItem, PlotItem
from qtpy.QtGui import QTransform, QPolygonF
from qtpy.QtWidgets import QLabel, QErrorMessage, QSizePolicy, QPushButton
from qtpy.QtCore import Qt, Signal, Slot, QSize, QPointF, QRectF
import numpy as np
from pyFAI.geometry import Geometry
from xicam.gui.widgets.elidedlabel import ElidedLabel
from xicam.gui.widgets.ROI import BetterPolyLineROI
from xicam.core import msg
import enum


# NOTE: PyQt widget mixins have pitfalls; note #2 here: http://trevorius.com/scrapbook/python/pyqt-multiple-inheritance/

# NOTE: PyFAI geometry position vector is: x = up
#                                          y = right
#                                          z = beam

# TODO: Add notification when qgrid is very wrong

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
    raw = enum.auto
    cake = enum.auto
    remesh = enum.auto


class QSpace(ImageView):
    def __init__(self, *args, geometry: Geometry = None, **kwargs):
        self._transform = QTransform()
        self.displaymode = DisplayMode.raw

        # Add q axes
        self.axesItem = PlotItem()
        self.axesItem.axes['left']['item'].setZValue(10)
        self.axesItem.axes['top']['item'].setZValue(10)
        if 'view' not in kwargs: kwargs['view'] = self.axesItem

        super(QSpace, self).__init__(*args, **kwargs)

        self.setGeometry(geometry)

    def setGeometry(self, geometry: Geometry):
        if callable(geometry):
            geometry = geometry()
        self._geometry = geometry
        self.setTransform()

    def setDisplayMode(self, mode):
        self.displaymode = mode
        self.setTransform()

    def setTransform(self):
        if self.imageItem.image is not None:
            shape = self.imageItem.image.shape
            qbottomright = np.array([shape[1], 0])
            qtopright = np.array([shape[1], shape[0]])
            qtopleft = np.array([0, shape[0]])
            qbottomleft = np.array([0, 0])
            self.axesItem.setLabel('bottom', u'x (px)')  # , units='s')
            self.axesItem.setLabel('left', u'z (px)')

            if self._geometry:
                # TODO: move to the hint system
                if self.displaymode == DisplayMode.remesh:
                    from camsaxs import remesh_bbox

                    self.axesItem.setLabel('bottom', u'q (Å⁻¹)')  # , units='s')
                    self.axesItem.setLabel('left', u'q (Å⁻¹)')

                    shape = self._geometry.detector.max_shape
                    z, y, x = self._geometry.calc_pos_zyx(*[np.array([0])] * 3)
                    topleftpos = np.array([x, y, z]).flatten()

                    z, y, x = self._geometry.calc_pos_zyx(np.array([0]), np.array([0]), np.array([shape[1]]))
                    toprightpos = np.array([x, y, z]).flatten()
                    #
                    z, y, x = self._geometry.calc_pos_zyx(np.array([0]), np.array([shape[0]]), np.array([shape[1]]))
                    bottomrightpos = np.array([x, y, z]).flatten()
                    #
                    z, y, x = self._geometry.calc_pos_zyx(np.array([0]), np.array([shape[0]]), np.array([0]))
                    bottomleftpos = np.array([x, y, z]).flatten()

                    qbottomleft = q_from_angles(phi(*bottomleftpos), alpha(*bottomleftpos),
                                                self._geometry.wavelength) * 1e-10 * np.array([1, -1, 1])
                    qbottomright = q_from_angles(phi(*bottomrightpos), alpha(*bottomrightpos),
                                                 self._geometry.wavelength) * 1e-10 * np.array([1, -1, 1])
                    qtopright = q_from_angles(phi(*toprightpos), alpha(*toprightpos),
                                              self._geometry.wavelength) * 1e-10 * np.array([1, -1, 1])
                    qtopleft = q_from_angles(phi(*topleftpos), alpha(*topleftpos),
                                             self._geometry.wavelength) * 1e-10 * np.array([1, -1, 1])

                    # qbottomleft = np.array(bottomleftpos[:2]) * np.array([1, -1])
                    # qbottomright = np.array(bottomrightpos[:2]) * np.array([1, -1])
                    # qtopright = np.array(toprightpos[:2]) * np.array([1, -1])
                    # qtopleft = np.array(topleftpos[:2]) * np.array([1, -1])

            # Build Quads
            quad1 = QPolygonF()
            quad1.append(QPointF(0, shape[0]))
            quad1.append(QPointF(shape[1], shape[0]))
            quad1.append(QPointF(shape[1], 0))
            quad1.append(QPointF(0, 0))

            quad2 = QPolygonF()
            quad2.append(QPointF(*qbottomleft[:2]))
            quad2.append(QPointF(*qbottomright[:2]))
            quad2.append(QPointF(*qtopright[:2]))
            quad2.append(QPointF(*qtopleft[:2]))

            # What did I build?
            msg.logMessage('qbottomleft:', np.array(qbottomleft[:2]))
            msg.logMessage('qbottomright:', np.array(qbottomright[:2]))
            msg.logMessage('qtopright:', np.array(qtopright[:2]))
            msg.logMessage('qtopleft:', np.array(qtopleft[:2]))

            transform = QTransform()
            QTransform.quadToQuad(quad1, quad2, transform)

            # # Invert Y axis (correct data dimensioning)
            # transform = QTransform()
            #
            # # Translate to Q-space
            # transform.translate(qtopleft[0]*1e-10, qtopleft[2]*1e-10)
            #
            # # Scale to Q-space
            # # transform.scale(1, -1)
            # transform.scale(((qbottomright[0]-qbottomleft[0])*1e-10)/shape[1],
            #                           ((qtopleft[2] - qbottomleft[2]) * 1e-10)/shape[0])

            # # Translate to Q-space
            # transform.translate(qbottomleft[0]*1e-10, (qbottomleft[2]+qtopright[2]-qbottomleft[2])*1e-10)

            for item in self.view.items:
                if isinstance(item, ImageItem):
                    item.setTransform(transform)
            self._transform = transform

    def setImage(self, *args, **kwargs):
        super(QSpace, self).setImage(*args, **kwargs)
        self.setTransform()


class CenterMarker(QSpace):

    def __init__(self, *args, **kwargs):
        self.centerplot = ScatterPlotItem(brush='r')
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
            x = 0  # fit2d['centerX']
            y = 0  # fit2d['centerY']
            self.centerplot.setData(x=[x], y=[y])

    def setGeometry(self, geometry: Geometry):
        super(CenterMarker, self).setGeometry(geometry)
        self.drawCenter()


class Crosshair(ImageView):
    def __init__(self, *args, **kwargs):
        super(Crosshair, self).__init__(*args, **kwargs)
        linepen = mkPen('#FFA500')
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


class QCoordinates(ImageView):
    def __init__(self, *args, **kwargs):
        super(QCoordinates, self).__init__(*args, **kwargs)

        self._coordslabel = QLabel(u"<div style='font-size:12pt;background-color:#111111; "
                                   u"text-overflow: ellipsis; width:100%;'>&nbsp;</div>")

        # def sizeHint():
        #     sizehint = QSize(self.ui.graphicsView.width()-10, self._coordslabel.height())
        #     return sizehint
        # self._coordslabel.sizeHint = sizeHint
        self._coordslabel.setSizePolicy(QSizePolicy.Ignored,
                                        QSizePolicy.Ignored)  # TODO: set sizehint to take from parent, not text
        self.ui.gridLayout.addWidget(self._coordslabel, 2, 0, 1, 1, alignment=Qt.AlignHCenter)

        self.scene.sigMouseMoved.connect(self.displayCoordinates)

    def displayCoordinates(self, pos):
        """
        when the mouse is moved in the viewer, translate the crosshair, recalculate coordinates
        """
        if self.view.sceneBoundingRect().contains(pos):
            mousePoint = self.view.getViewBox().mapSceneToView(pos)
            x, y = mousePoint.x(), mousePoint.y()
            if self.imageItem.mapRectToView(self.imageItem.boundingRect()).contains(mousePoint):  # within bounds
                # angstrom=QChar(0x00B5)
                pxpos = self.imageItem.mapFromView(QPointF(x, y))
                try:
                    I = self.imageItem.image[int(pxpos.y()), int(pxpos.x())]
                except IndexError:
                    I = 0
                self._coordslabel.setText(f"<div style='font-size: 12pt;background-color:#111111; "
                                          f"text-overflow: ellipsis; width:100%;'>"
                                          f"x={pxpos.x():0.1f}, "
                                          f"<span style=''>y={self.imageItem.image.shape[0]-pxpos.y():0.1f}</span>, "
                                          f"<span style=''>I={I:0.0f}</span>, "
                                          f"q={np.sqrt(x**2+y**2):0.3f} \u212B\u207B\u00B9, "
                                          f"q<sub>z</sub>={y:0.3f} \u212B\u207B\u00B9, "
                                          f"q<sub>\u2225</sub>={x:0.3f} \u212B\u207B\u00B9, "
                                          f"d={2*np.pi/np.sqrt(x**2+y**2)*10:0.3f} nm, "
                                          f"\u03B8={np.deg2rad(np.arctan2(y,x)):.2f}&#176;</div>")
                # if self.plotwidget is not None:  # for timeline
                #     self.plotwidget.movPosLine(self.getq(x, y),
                #                                self.getq(x, y, mode='parallel'),
                #                                self.getq(x, y, mode='z'))

            else:
                self._coordslabel.setText(u"<div style='font-size:12pt;background-color:#111111;'>&nbsp;</div>")
                # if hasattr(self.plotwidget, 'qintegration'):
                #     self.plotwidget.qintegration.posLine.hide()


class BetterButtons(ImageView):
    def __init__(self, *args, **kwargs):
        super(BetterButtons, self).__init__(*args, **kwargs)

        # Setup axes reset button
        self.resetAxesBtn = QPushButton('Reset Axes')
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.resetAxesBtn.sizePolicy().hasHeightForWidth())
        self.resetAxesBtn.setSizePolicy(sizePolicy)
        self.resetAxesBtn.setObjectName("resetAxes")
        self.ui.gridLayout.addWidget(self.resetAxesBtn, 2, 1, 1, 1)
        self.resetAxesBtn.clicked.connect(self.autoRange)

        # Setup LUT reset button
        self.resetLUTBtn = QPushButton('Reset LUT')
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.resetLUTBtn.sizePolicy().hasHeightForWidth())
        # self.resetLUTBtn.setSizePolicy(sizePolicy)
        # self.resetLUTBtn.setObjectName("resetLUTBtn")
        self.ui.gridLayout.addWidget(self.resetLUTBtn, 2, 2, 1, 1)
        self.resetLUTBtn.clicked.connect(self.autoLevels)

        # Hide ROI button and rearrange
        self.ui.roiBtn.setParent(None)
        self.ui.menuBtn.setParent(None)
        # self.ui.gridLayout.addWidget(self.ui.menuBtn, 1, 1, 1, 1)
        self.ui.gridLayout.addWidget(self.ui.graphicsView, 0, 0, 2, 1)


class PolygonROI(ImageView):
    def __init__(self, *args, **kwargs):
        super(PolygonROI, self).__init__(*args, **kwargs)
        rect = self.imageItem.boundingRect()  # type: QRectF
        positions = [(rect.bottomLeft().x(), rect.bottomLeft().y()),
                     (rect.bottomRight().x(), rect.bottomRight().y()),
                     (rect.topRight().x(), rect.topRight().y()),
                     (rect.topLeft().x(), rect.topLeft().y())]
        self._roiItem = BetterPolyLineROI(positions=positions, closed=True)
        self.addItem(self._roiItem)
