from pyqtgraph.parametertree import ParameterTree
from pyqtgraph.parametertree.parameterTypes import Parameter, GroupParameter
from collections import deque, OrderedDict, defaultdict
from qtpy.QtGui import QStandardItem, QStandardItemModel
from qtpy.QtCore import QItemSelectionModel, Signal
import sys
import uuid
import datetime
import numpy as np
import warnings
from typing import Iterable, Sequence
from xicam.core import msg
from xicam.core.data import NonDBHeader
from xicam.gui.patches.PyQtGraph import CounterGroupParameter, LazyGroupParameter

# TODO: map list to groupparameter

# TODO: suggest integration of type mapping into pyqtgraph
typemap = {
    int: "int",
    float: "float",
    np.float64: "float",
    str: "str",
    dict: "lazygroup",
    OrderedDict: "lazygroup",
    list: "lazygroup",
    type(None): None,
    tuple: "lazygroup",
    datetime.datetime: "str",
    np.float: "float",
    np.ndarray: "ndarray",
    np.int: "int",
}


class MetadataWidgetBase(ParameterTree):
    def __init__(self, *args, **kwargs):
        self.excludedkeys = kwargs.get("excludedkeys")
        if "excludedkeys" in kwargs:
            del kwargs["excludedkeys"]

        super(MetadataWidgetBase, self).__init__(*args, **kwargs)
        LazyGroupParameter.itemClass.initialize_treewidget(self)
        self.kwargs = kwargs

    def insert(self, doctype: str, document, groups: dict):
        if doctype == "start":
            for group in groups.values():
                group.clearChildren()

        try:
            new_children = MetadataView._from_dict(document, self.excludedkeys)
        except Exception as ex:
            msg.logError(ex)
            print(f"failed to make children for {doctype}")
        else:
            # TODO: add responsive design to uid display
            group = groups[doctype]
            group.addChildren(
                [
                    GroupParameter(
                        name=document["uid"][:6], value=None, type=None, children=new_children, expanded=False, readonly=True
                    )
                ]
            )

    @staticmethod
    def _from_dict(metadata: Iterable, excludedkeys=None):
        if isinstance(metadata, Sequence):
            metadata = OrderedDict(enumerate(metadata))

        metadata = MetadataView._strip_reserved(metadata, excludedkeys)
        children = []
        for key, value in metadata.items():
            subchildren = []
            if typemap.get(type(value), None) in ["group", "lazygroup"]:
                subchildren = MetadataView._from_dict(value)
                key = f"{str(key)} {type(value)}"
                value = None
            try:
                children.append(
                    Parameter.create(
                        name=str(key),
                        value=value,
                        type=typemap[type(value)],
                        children=subchildren,
                        expanded=False,
                        readonly=True,
                    )
                )
            except KeyError:
                warnings.warn(f"Failed to display a {type(value)}: {value}")
                children.append(
                    Parameter.create(
                        name=str(key),
                        value=repr(value),
                        type=typemap[str],
                        children=subchildren,
                        expanded=False,
                        readonly=True,
                    )
                )
        return children

    @staticmethod
    def _strip_reserved(metadata: dict, excludedkeys=None):
        if not excludedkeys:
            excludedkeys = []
        metadata = metadata.copy()
        for key in excludedkeys:
            if key in metadata:
                del metadata[key]
        return metadata


class MetadataWidget(MetadataWidgetBase):
    def __init__(self, *args, **kwargs):
        super(MetadataWidget, self).__init__(*args, **kwargs)
        self.header = None  # type: HeaderParameter
        self.groups = dict()
        self.reset()

    def doc_consumer(self, name, doc):
        if name == "start":
            self.header.setName(doc["uid"])
        super(MetadataWidget, self).insert(name, doc, self.groups)

    def reset(self):
        self.header = HeaderParameter(name=" ")
        self.groups = {group.name(): group for group in self.header.children()}
        self.setParameters(self.header)


class MetadataView(MetadataWidgetBase):
    sigUpdate = Signal()

    def __init__(self, headermodel: QStandardItemModel, selectionmodel: QItemSelectionModel, *args, **kwargs):
        super(MetadataView, self).__init__(*args, **kwargs)
        self._seen = set()
        self._last_uid = None
        self._thread_id = "MetadataView" + str(uuid.uuid4())
        self.headermodel = headermodel
        self.selectionmodel = selectionmodel
        self.selectionmodel.currentChanged.connect(self.update)
        self.sigUpdate.connect(self.update)
        self.update()

    def update(self):
        index = self.selectionmodel.currentIndex()
        if not index.isValid():
            return

        header = self.headermodel.itemFromIndex(index).header  # type: NonDBHeader

        if header.startdoc["uid"] != self._last_uid:
            self._seen = set()

        if not isinstance(header, HeaderBuffer):
            headerbuffer = HeaderBuffer(
                header.startdoc["uid"], HeaderParameter(name=header.startdoc["uid"]), docs=header.documents()
            )

        param = headerbuffer.param
        groups = param.groups

        # TODO: make compatible with actively streaming header

        # filter out documents already emitted in the stream
        for doctype, document in header.stream():
            if document["uid"] in self._seen:
                continue

            self._seen.add(document["uid"])
            self.insert(doctype, document, groups)

        if headerbuffer.uid != self._last_uid:
            self._last_uid = headerbuffer.uid
            # try:
            self.setParameters(param, showTop=False)


class HeaderParameter(GroupParameter):
    def __init__(self, *args, **kwargs):
        super(HeaderParameter, self).__init__(*args, **kwargs)

        self.groups = {
            "start": CounterGroupParameter(name="start", title="Start", expanded=False),
            "descriptor": CounterGroupParameter(name="descriptor", title="Descriptors", expanded=False),
            "event": CounterGroupParameter(name="event", title="Events", expanded=False),
            "stop": CounterGroupParameter(name="stop", title="Stop", expanded=False),
        }
        self.addChildren(self.groups.values())


class HeaderBuffer:
    def __init__(self, uid, param: GroupParameter, docs=None):
        self.uid = uid
        self.buf = deque()
        self.param = param

        for name, doc in docs:
            self.buf.append((name, doc))

    def stream(self, *args):
        yield from self.buf


class MDVConusumer(MetadataView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._buffers = {}
        self._descriptor_map = {}

    def doc_consumer(self, name, doc):
        if name == "start":
            uid = doc["uid"]
            item = QStandardItem(doc["uid"])
            item.header = self._buffers[uid] = HeaderBuffer(uid, HeaderParameter(name="uid"))
            self.headermodel.appendRow(item)
            self.selectionmodel.setCurrentIndex(self.headermodel.indexFromItem(item), QItemSelectionModel.ClearAndSelect)
        elif name == "descriptor":
            uid = self._descriptor_map[doc["uid"]] = doc["run_start"]
        elif name == "event":
            uid = self._descriptor_map[doc["descriptor"]]
        elif name == "stop":
            uid = doc["run_start"]
        else:
            raise ValueError

        buffer = self._buffers[uid].buf  # type: deque
        buffer.append((name, doc))
        self.sigUpdate.emit()

    def show_row_n(self, n):
        item = self.headermodel.item(n)
        if item is None:
            return
        self.selectionmodel.setCurrentIndex(self.headermodel.indexFromItem(item), QItemSelectionModel.ClearAndSelect)
        self.update()


if __name__ == "__main__":
    import os

    os.environ["OPHYD_CONTROL_LAYER"] = "caproto"
    from qtpy import QtWidgets
    from qtpy import QtCore
    from qtpy import QtGui
    from mily.runengine import spawn_RE
    from mily.widgets import ControlGui, Count, Scan1D, MotorSelector, DetectorSelector, MISpin
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

            self.spinner = spinner = MISpin("run")
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
    hw.motor.delay = 0.1
    hw.motor1.delay = 0.2
    hw.motor2.delay = 0.3

    hw.det.kind = "hinted"
    hw.det1.kind = "hinted"
    hw.det2.kind = "hinted"

    RE, queue, thread, teleport = spawn_RE()

    cg = ControlGui(
        queue,
        teleport,
        Count("Count", bp.count, DetectorSelector(detectors=[hw.det, hw.det1, hw.det2])),
        Scan1D(
            "1D absolute scan",
            bp.scan,
            MotorSelector([hw.motor, hw.motor1, hw.motor2]),
            DetectorSelector(detectors=[hw.det, hw.det1, hw.det2]),
        ),
        Scan1D(
            "1D relative scan",
            bp.rel_scan,
            MotorSelector([hw.motor, hw.motor1, hw.motor2]),
            DetectorSelector(detectors=[hw.det, hw.det1, hw.det2]),
        ),
        live_widget=view_box,
    )

    cg.show()
    sys.exit(app.exec_())
