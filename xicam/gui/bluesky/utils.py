import inspect

from PyQt5.QtGui import QCursor, QDrag, QPixmap, QRegion
from PyQt5.QtWidgets import QWidget, QTabWidget
from PyQt5.QtCore import Qt, QMimeData, QObject, QPoint
from traitlets import HasTraits, TraitType
from traitlets.config import Configurable


class MoveableTabWidget(QTabWidget):
    """
    Adapted from https://stackoverflow.com/a/46719634/1221924
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self.tabBar().setMouseTracking(True)
        self.indexTab = None
        self.setMovable(True)

    def mouseMoveEvent(self, e):
        if e.buttons() != Qt.RightButton:
            return

        globalPos = self.mapToGlobal(e.pos())
        tabBar = self.tabBar()
        posInTab = tabBar.mapFromGlobal(globalPos)
        self.indexTab = tabBar.tabAt(e.pos())
        tabRect = tabBar.tabRect(self.indexTab)

        pixmap = QPixmap(tabRect.size())
        tabBar.render(pixmap, QPoint(), QRegion(tabRect))
        mimeData = QMimeData()
        drag = QDrag(tabBar)
        drag.setMimeData(mimeData)
        drag.setPixmap(pixmap)
        cursor = QCursor(Qt.OpenHandCursor)
        drag.setHotSpot(e.pos() - posInTab)
        drag.setDragCursor(cursor.pixmap(), Qt.MoveAction)
        drag.exec_(Qt.MoveAction)

    def dragEnterEvent(self, e):
        e.accept()
        if e.source().parentWidget() != self:
            return

        # print(self.indexOf(self.widget(self.indexTab)))
        self.parent().tab_index = self.indexOf(self.widget(self.indexTab))

    def dragLeaveEvent(self, e):
        e.accept()

    def dropEvent(self, e):
        if e.source().parentWidget() == self:
            return

        e.setDropAction(Qt.MoveAction)
        e.accept()
        counter = self.count()

        if counter == 0:
            self.addTab(e.source().parentWidget().widget(self.parent().tab_index),
                        e.source().tabText(self.parent().tab_index))
        else:
            self.insertTab(counter + 1,
                           e.source().parentWidget().widget(self.parent().tab_index),
                           e.source().tabText(self.parent().tab_index))


class MoveableTabContainer(QWidget):
    """
    Adapted from https://stackoverflow.com/a/46719634/1221924
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tab_index = 0
        self.moveWidget = None  # not needed?


# These classes integrate Qt and traitlets so that we can subclass both.
# They are copied from Jupyter's qtconsole.util package. The only edits made
# here are removing PY2 support.


MetaHasTraits = type(HasTraits)
MetaQObject = type(QObject)


class MetaQObjectHasTraits(MetaQObject, MetaHasTraits):
    """ A metaclass that inherits from the metaclasses of HasTraits and QObject.
    Using this metaclass allows a class to inherit from both HasTraits and
    QObject. Using SuperQObject instead of QObject is highly recommended. See
    QtKernelManager for an example.
    """
    def __new__(mcls, name, bases, classdict):
        # FIXME: this duplicates the code from MetaHasTraits.
        # I don't think a super() call will help me here.
        for k, v in classdict.items():
            if isinstance(v, TraitType):
                v.name = k
            elif inspect.isclass(v):
                if issubclass(v, TraitType):
                    vinst = v()
                    vinst.name = k
                    classdict[k] = vinst
        cls = MetaQObject.__new__(mcls, name, bases, classdict)
        return cls

    def __init__(mcls, name, bases, classdict):
        # Note: super() did not work, so we explicitly call these.
        MetaQObject.__init__(mcls, name, bases, classdict)
        MetaHasTraits.__init__(mcls, name, bases, classdict)


def superQ(QClass):
    """ Permits the use of super() in class hierarchies that contain Qt classes.
    Unlike QObject, SuperQObject does not accept a QObject parent. If it did,
    super could not be emulated properly (all other classes in the heierarchy
    would have to accept the parent argument--they don't, of course, because
    they don't inherit QObject.)
    This class is primarily useful for attaching signals to existing non-Qt
    classes. See QtKernelManagerMixin for an example.
    """
    class SuperQClass(QClass):

        def __new__(cls, *args, **kw):
            # We initialize QClass as early as possible. Without this, Qt complains
            # if SuperQClass is not the first class in the super class list.
            inst = QClass.__new__(cls)
            QClass.__init__(inst)
            return inst

        def __init__(self, *args, **kw):
            # Emulate super by calling the next method in the MRO, if there is one.
            mro = self.__class__.mro()
            for qt_class in QClass.mro():
                mro.remove(qt_class)
            next_index = mro.index(SuperQClass) + 1
            if next_index < len(mro):
                mro[next_index].__init__(self, *args, **kw)

    return SuperQClass


SuperQObject = superQ(QObject)
ConfigurableQObject = MetaQObjectHasTraits(
    'NewBase', (Configurable, SuperQObject), {})
ConfigurableQTabWidget = MetaQObjectHasTraits(
    'NewBase', (Configurable, QTabWidget, SuperQObject), {})
ConfigurableMoveableTabContainer = MetaQObjectHasTraits(
    'NewBase', (Configurable, MoveableTabContainer, SuperQObject), {})
