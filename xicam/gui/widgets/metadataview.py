from pyqtgraph.parametertree import ParameterTree, Parameter
from pyqtgraph.parametertree.parameterTypes import SimpleParameter, GroupParameter
from qtpy.QtGui import *
from qtpy.QtWidgets import *
from qtpy.QtCore import *

# TODO: suggest integration of type mapping into pyqtgraph
typemap = {int: 'int',
           float: 'float',
           str: 'str',
           dict: 'group',
           type(None): None
           }

reservedkeys = ['data', ]


class MetadataView(ParameterTree):
    def __init__(self, headermodel: QStandardItemModel, selectionmodel: QItemSelectionModel, *args, **kwargs):
        super(MetadataView, self).__init__(*args, **kwargs)
        self.headermodel = headermodel
        self.selectionmodel = selectionmodel
        self.selectionmodel.selectionChanged.connect(self.update)

        self.update()

    def update(self):
        index = self.selectionmodel.currentIndex()
        if not index.isValid():
            return
        header = self.headermodel.itemFromIndex(index).header
        groups = {'start': GroupParameter(name='Start'),
                  'descriptor': GroupParameter(name='Descriptors'),
                  'event': GroupParameter(name='Events'),
                  'stop': GroupParameter(name='Stop')}
        children = list(groups.values())
        for doctype, document in header.stream():
            groups[doctype].addChildren(MetadataView._from_dict(document))

        param = GroupParameter(name='Metadata', children=children)
        self.setParameters(param, showTop=False)

    @staticmethod
    def _from_dict(metadata: dict):
        metadata = MetadataView._strip_reserved(metadata)
        children = []
        for key, value in metadata.items():
            subchildren = []
            paramcls = SimpleParameter
            if typemap[type(value)] == 'group':
                subchildren = MetadataView._from_dict(value)
                value = None
                paramcls = GroupParameter
            children.append(paramcls(name=key, value=value, type=typemap[type(value)], children=subchildren))
        return children

    @staticmethod
    def _strip_reserved(metadata: dict):
        metadata = metadata.copy()
        for key in reservedkeys:
            if key in metadata:
                del metadata[key]
        return metadata


if __name__ == '__main__':
    qapp = QApplication([])

    headermodel = QStandardItemModel()
    selectionmodel = QItemSelectionModel(headermodel)
    item = QStandardItem('example.tif')
    headermodel.appendRow(item)
    selectionmodel.setCurrentIndex(headermodel.indexFromItem(item), QItemSelectionModel.ClearAndSelect)


    class header(object):
        stream = lambda *_: [('event', {'data': {'temperature': 5.0, 'position': 3.0},
                                        'timestamps': {'temperature': 1442521007.9258342,
                                                       'position': 1442521007.5029348},
                                        'time': 1442521007.3438923,
                                        'uid': '1',
                                        'descriptor': '2',
                                        })]


    item.header = header()
    metadataview = MetadataView(headermodel, selectionmodel)

    metadataview.show()

    qapp.exec_()
