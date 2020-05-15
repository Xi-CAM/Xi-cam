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

    @staticmethod
    def guess_stream_field(catalog: BlueskyRun):
        # TODO: use some metadata (techniques?) for guidance about how to get a preview

        streams = bluesky_utils.streams_from_run(catalog)
        if "primary" in streams:
            streams.remove("primary")
            streams.insert(0, "primary")

        for stream in streams:
            descriptor = bluesky_utils.descriptors_from_stream(catalog, stream)[0]
            fields = bluesky_utils.fields_from_descriptor(descriptor)
            for field in fields:
                field_ndims = bluesky_utils.ndims_from_descriptor(descriptor, field)
                if field_ndims > 1:
                    return stream, field

    def preview_catalog(self, catalog: BlueskyRun):
        threads.invoke_in_main_thread(self.setText, "LOADING...")
        try:
            stream, field = self.guess_stream_field(catalog)
            data = getattr(catalog, stream).to_dask()[field].squeeze()
            for i in range(len(data.shape) - 2):
                data = data[0]
            threads.invoke_in_main_thread(self.setImage, np.asarray(data.compute()))
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
