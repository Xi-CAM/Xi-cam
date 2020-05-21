from databroker.core import BlueskyRun
from pyqtgraph import ImageItem, TextItem, GraphicsLayoutWidget
import numpy as np
from qtpy.QtCore import QSize
from qtpy.QtGui import QFont, QTransform
from qtpy.QtWidgets import QSizePolicy
from xicam.core import msg, threads
from xicam.core.data import bluesky_utils

from xicam.core.data import NonDBHeader


class PreviewWidget(GraphicsLayoutWidget):
    def __init__(self):
        super(PreviewWidget, self).__init__()
        self.setMinimumHeight(250)
        self.setMinimumWidth(250)
        self.view = self.addViewBox(lockAspect=True, enableMenu=False)
        self.imageitem = ImageItem()
        self.textitem = TextItem(anchor=(0.5, 0))
        self.textitem.setFont(QFont("Zero Threes"))
        self.imgdata = None

        self.imageitem.setOpts(axisOrder="row-major")

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

    @threads.method(threadkey="preview", showBusy=False)
    def preview(self, data):
        if isinstance(data, NonDBHeader):
            self.preview_header(data)
        else:
            self.preview_catalog(data)

    def preview_catalog(self, catalog: BlueskyRun):
        threads.invoke_in_main_thread(self.setText, "LOADING...")
        try:
            stream, field = bluesky_utils.guess_stream_field(catalog)
            data = bluesky_utils.preview(catalog, stream, field)
            threads.invoke_in_main_thread(self.setImage, data)
        except Exception as ex:
            msg.logError(ex)
            threads.invoke_in_main_thread(self.imageitem.clear)
            threads.invoke_in_main_thread(self.setText, "UNKNOWN DATA FORMAT")

    def preview_header(self, header: NonDBHeader):
        try:
            data = header.meta_array()[0]
            threads.invoke_in_main_thread(self.setImage, data)
        except IndexError:
            threads.invoke_in_main_thread(self.imageitem.clear)
            threads.invoke_in_main_thread(self.setText, "UNKNOWN DATA FORMAT")

    def setImage(self, imgdata):
        self.imageitem.clear()
        self.textitem.hide()
        self.imgdata = imgdata
        self.imageitem.setImage(np.log(self.imgdata * (self.imgdata > 0) + (self.imgdata < 1)), autoLevels=True)
        self.imageitem.setTransform(QTransform(1, 0, 0, -1, 0, self.imgdata.shape[-2]))
        self.view.autoRange()

    def setText(self, text):
        self.textitem.setText(text)
        self.imageitem.clear()
        self.textitem.setVisible(True)
        self.view.autoRange()
