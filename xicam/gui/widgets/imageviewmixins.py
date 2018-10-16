from functools import WRAPPER_ASSIGNMENTS
from pyqtgraph import ImageView, InfiniteLine, mkPen, ScatterPlotItem
from qtpy.QtWidgets import QLabel, QErrorMessage, QSizePolicy, QPushButton
from qtpy.QtCore import Qt, Signal, Slot, QSize
import numpy as np
from pyFAI.geometry import Geometry
from xicam.gui.widgets.elidedlabel import ElidedLabel


# NOTE: PyQt widget mixins have pitfalls; note #2 here: http://trevorius.com/scrapbook/python/pyqt-multiple-inheritance/


class QSpace(ImageView):
    sigGeometryChanged = Signal()

    def __init__(self, *args, geometry: Geometry = None, **kwargs):
        super(QSpace, self).__init__(*args, **kwargs)

        self.setGeometry(geometry)

    def setGeometry(self, geometry: Geometry):
        if callable(geometry):
            geometry = geometry()
        self._geometry = geometry
        self.sigGeometryChanged.emit()


class CenterMarker(QSpace):
    sigGeometryChanged = Signal()

    def __init__(self, *args, **kwargs):
        super(CenterMarker, self).__init__(*args, **kwargs)

        self.centerplot = ScatterPlotItem(brush='r')
        self.centerplot.setZValue(100)
        self.addItem(self.centerplot)
        self.sigGeometryChanged.connect(self.drawCenter)
        self.drawCenter()

    def drawCenter(self):
        try:
            fit2d = self._geometry.getFit2D()
        except (TypeError, AttributeError):
            pass
        else:
            x = fit2d['centerX']
            y = fit2d['centerY']
            self.centerplot.setData(x=[x], y=[y])


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
            if self.imageItem.boundingRect().contains(mousePoint):  # within bounds
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
            if self.imageItem.boundingRect().contains(mousePoint):  # within bounds
                # angstrom=QChar(0x00B5)
                self._coordslabel.setText(f"<div style='font-size: 12pt;background-color:#111111; "
                                          f"text-overflow: ellipsis; width:100%;'>"
                                          f"x={0:0.1f}, "
                                          f"<span style=''>y={0:0.1f}</span>, "
                                          f"<span style=''>I={0:0.0f}</span>, "
                                          f"q={np.sqrt(x**2+y**2):0.3f} \u212B\u207B\u00B9, "
                                          f"q<sub>z</sub>={y:0.3f} \u212B\u207B\u00B9, "
                                          f"q<sub>\u2225</sub>={x:0.3f} \u212B\u207B\u00B9, "
                                          f"d={0:0.3f} nm, "
                                          f"\u03B8={np.arctan2(y,x):.2f}</div>")
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
