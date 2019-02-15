from pyqtgraph.parametertree import ParameterTree
from pyqtgraph.parametertree.parameterTypes import (SimpleParameter,
                                                    GroupParameter)
from collections import deque
from qtpy.QtGui import (QStandardItem, QStandardItemModel)
from qtpy.QtCore import QItemSelectionModel
import sys

# TODO: suggest integration of type mapping into pyqtgraph
typemap = {int: 'int',
           float: 'float',
           str: 'str',
           dict: 'group',
           type(None): None
           }

reservedkeys = []


class MetadataView(ParameterTree):
    def __init__(self, headermodel: QStandardItemModel,
                 selectionmodel: QItemSelectionModel,
                 *args, **kwargs):
        super(MetadataView, self).__init__(*args, **kwargs)
        self.headermodel = headermodel
        self.selectionmodel = selectionmodel
        self.selectionmodel.selectionChanged.connect(self.update)

        self._seen = set()
        self._last_uid = None
        self.update()

    def update(self):
        index = self.selectionmodel.currentIndex()
        if not index.isValid():
            return
        header = self.headermodel.itemFromIndex(index).header
        groups = header.groups
        param = header.param

        for doctype, document in header.stream():
            if document['uid'] in self._seen:
                continue
            self._seen.add(document['uid'])
            try:
                new_children = MetadataView._from_dict(document)
            except Exception:
                print(f'failed to make children or {doctype}')
            groups[doctype].addChildren([
                GroupParameter(name=document['uid'][:6],
                               value=None,
                               type=None,
                               children=new_children)])
        if header.uid != self._last_uid:
            self._last_uid = header.uid
            try:
                self.setParameters(param)
            except AttributeError:
                # there seems to be a race condition here?!
                self.setParameters(param)

    @staticmethod
    def _from_dict(metadata: dict):
        metadata = MetadataView._strip_reserved(metadata)
        children = []
        for key, value in metadata.items():
            subchildren = []
            paramcls = SimpleParameter
            if typemap.get(type(value), None) == 'group':
                subchildren = MetadataView._from_dict(value)
                value = None
                paramcls = GroupParameter
            try:
                children.append(paramcls(name=key,
                                         value=value,
                                         type=typemap[type(value)],
                                         children=subchildren))
            except KeyError:
                print(f'failed on {value}: {type(value)}')
                children.append(paramcls(name=key,
                                         value=repr(value),
                                         type=typemap[str],
                                         children=subchildren))
        return children

    @staticmethod
    def _strip_reserved(metadata: dict):
        metadata = metadata.copy()
        for key in reservedkeys:
            if key in metadata:
                del metadata[key]
        return metadata


class HeaderBuffer:
    def __init__(self, groups, param, uid):
        self.groups = groups
        self.param = param
        self.uid = uid
        self.buf = deque()

    def stream(self, *args):
        yield from self.buf


class MDVConusumer(MetadataView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._buffers = {}

    def doc_consumer(self, name, doc):

        if name == 'start':
            uid = doc['uid']
            groups = {'start': GroupParameter(name='Start'),
                      'descriptor': GroupParameter(name='Descriptors'),
                      'event': GroupParameter(name='Events'),
                      'stop': GroupParameter(name='Stop')}
            param = GroupParameter(name='Metadata',
                                   children=groups.values())
            hb = self._buffers[uid] = HeaderBuffer(groups, param, uid)
            hb.buf.append((name, doc))
            item = QStandardItem(doc['uid'])

            item.header = hb
            self.headermodel.appendRow(item)
            self.selectionmodel.setCurrentIndex(
                self.headermodel.indexFromItem(item),
                QItemSelectionModel.ClearAndSelect)
        elif name == 'descriptor':
            hb = self._buffers[doc['run_start']]
            self._buffers[doc['uid']] = hb
            hb.buf.append((name, doc))
        elif name == 'event':
            hb = self._buffers[doc['descriptor']]
            hb.buf.append((name, doc))
        elif name == 'stop':
            hb = self._buffers[doc['run_start']]
            hb.buf.append((name, doc))

        self.update()

    def show_row_n(self, n):
        item = self.headermodel.item(n)
        if item is None:
            return
        self.selectionmodel.setCurrentIndex(
            self.headermodel.indexFromItem(item),
            QItemSelectionModel.ClearAndSelect)
        self.update()


if __name__ == '__main__':
    from qtpy import QtWidgets
    from qtpy import QtCore
    from qtpy import QtGui
    from mily.runengine import spawn_RE
    from mily.widgets import (ControlGui, Count, Scan1D, MotorSelector,
                              DetectorSelector, MISpin)
    import bluesky.plans as bp
    from ophyd.sim import hw
    import matplotlib

    matplotlib.interactive(True)

    class MDVWithButtons(QtWidgets.QWidget):
        def __init__(self, mdv, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.mdv = mdv

            w_layout = QtWidgets.QVBoxLayout()
            w_layout.addWidget(mdv)

            button_layout = QtWidgets.QHBoxLayout()
            w_layout.addLayout(button_layout)

            self.spinner = spinner = MISpin('run')
            w_layout.addWidget(spinner)
            spinner.setRange(0, 100)

            def on_change(n):
                self.mdv.show_row_n(n)

            spinner.valueChanged.connect(on_change)
            self.setLayout(w_layout)

        def doc_consumer(self, name, doc):
            self.mdv.doc_consumer(name, doc)
            self.spinner.setRange(0, self.mdv.headermodel.rowCount() - 1)

    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([b"Live data demo"])
        app.lastWindowClosed.connect(app.quit)

    headermodel = QtGui.QStandardItemModel()
    selectionmodel = QtCore.QItemSelectionModel(headermodel)

    metadataview = MDVConusumer(headermodel, selectionmodel)
    view_box = MDVWithButtons(metadataview)

    hw = hw()
    hw.motor.set(15)
    hw.motor.delay = .1
    hw.motor1.delay = .2
    hw.motor2.delay = .3

    hw.det.kind = 'hinted'
    hw.det1.kind = 'hinted'
    hw.det2.kind = 'hinted'

    RE, queue, thread, teleport = spawn_RE()

    cg = ControlGui(queue, teleport,
                    Count('Count', bp.count,
                          DetectorSelector(
                              detectors=[hw.det, hw.det1, hw.det2])),
                    Scan1D('1D absolute scan', bp.scan,
                           MotorSelector([hw.motor, hw.motor1, hw.motor2]),
                           DetectorSelector(
                               detectors=[hw.det, hw.det1, hw.det2])),
                    Scan1D('1D relative scan', bp.rel_scan,
                           MotorSelector([hw.motor, hw.motor1, hw.motor2]),
                           DetectorSelector(
                               detectors=[hw.det, hw.det1, hw.det2])),
                    live_widget=view_box,
                    )

    cg.show()
    sys.exit(app.exec_())
