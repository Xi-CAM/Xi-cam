from qtpy.QtCore import *
from qtpy.QtWidgets import *
from yapsy.IPlugin import IPlugin


# TODO: make classes usable without qt



# class _metaQWidgetPlugin(type(QObject), type(IPlugin)):
#     pass
#
#
# class QWidgetPlugin(metaclass=_metaQWidgetPlugin):
#     isSingleton = False


class QWidgetPlugin(QWidget, IPlugin):
    isSingleton = False


def test_QWidgetPlugin():
    from pyqtgraph import ImageView
    class ImageViewPlugin(QWidgetPlugin, ImageView):
        pass

    app = makeapp()
    i = ImageViewPlugin()
    i.show()
    t = QTimer()
    t.singleShot(1000, i.close)
    mainloop()


def makeapp():
    app = QApplication([])
    return app


def mainloop():
    app = QApplication.instance()
    app.exec_()
