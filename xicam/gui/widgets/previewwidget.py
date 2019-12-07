from databroker.core import BlueskyRun
from pyqtgraph import ImageItem, TextItem, GraphicsLayoutWidget
import numpy as np
from qtpy.QtCore import QSize
from qtpy.QtGui import QFont, QTransform
from qtpy.QtWidgets import QSizePolicy

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

    def preview(self, data):
        if isinstance(data, NonDBHeader):
            self.preview_header(data)
        else:
            self.preview_catalog(data)

    def preview_catalog(self, catalog: BlueskyRun):
        try:
            dask_array = catalog.primary.to_dask()
            fields = dask_array.keys()
            # Filter out seq num and uid
            field = next(field for field in fields if not field in ["seq_num", "uid"])
            data = dask_array[field]
            for i in range(len(data.shape) - 2):
                data = data[0]
            self.setImage(np.asarray(data.compute()))
        except IndexError:
            self.imageitem.clear()
            self.setText("UNKNOWN DATA FORMAT")

    def preview_header(self, header: NonDBHeader):
        try:
            data = header.meta_array()[0]
            self.setImage(data)
        except IndexError:
            self.imageitem.clear()
            self.setText("UNKNOWN DATA FORMAT")

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
