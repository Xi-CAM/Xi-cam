from qtpy.QtCore import QSize
from qtpy.QtGui import QFont
from qtpy.QtWidgets import QSizePolicy
from pyqtgraph import ImageItem, TextItem, GraphicsLayoutWidget
import os
from xicam.core.data import NonDBHeader
import numpy as np


class PreviewWidget(GraphicsLayoutWidget):
    def __init__(self):
        super(PreviewWidget, self).__init__()
        self.setMinimumHeight(250)
        self.setMinimumWidth(250)
        self.view = self.addViewBox(lockAspect=True, enableMenu=False)
        self.imageitem = ImageItem()
        self.textitem = TextItem(anchor=(0.5, 0))
        self.textitem.setFont(QFont('Zero Threes'))
        self.imgdata = None

        self.view.addItem(self.imageitem)
        self.view.addItem(self.textitem)
        self.textitem.hide()
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        # def textItemBounds(axis, frac=1.0, orthoRange=None):
        #     b = self.textitem.boundingRect()
        #     sx, sy = self.view.viewPixelSize()
        #     x, y = sx*b.width(), sy*b.height()
        #     if axis == 0: return (-x/2, x/2)
        #     if axis == 1: return (0, y)
        #
        # self.textitem.dataBounds = textItemBounds

    def sizeHint(self):
        return QSize(250, 250)

    def preview_header(self, header: NonDBHeader):
        try:
            data = header.meta_array()[0]
            self.setImage(data)
        except IndexError:
            self.imageitem.clear()
            self.setText('UNKNOWN DATA FORMAT')

    def setImage(self, imgdata):
        self.imageitem.clear()
        self.textitem.hide()
        self.imgdata = imgdata
        self.imageitem.setImage(np.rot90(np.log(self.imgdata * (self.imgdata > 0) + (self.imgdata < 1)), 3),
                                autoLevels=True)
        self.view.autoRange()

    def setText(self, text):
        self.textitem.setText(text)
        self.imageitem.clear()
        self.textitem.setVisible(True)
        self.view.autoRange()
