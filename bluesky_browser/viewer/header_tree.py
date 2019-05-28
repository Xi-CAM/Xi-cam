from collections.abc import Iterable
from datetime import datetime

from qtpy.QtWidgets import (
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
    QVBoxLayout,
)


def fill_item(item, value):
    """
    Display a dictionary as a QtTreeWidget

    adapted from http://stackoverflow.com/a/21806048/1221924
    """
    item.setExpanded(False)
    if hasattr(value, 'items'):
        for key, val in sorted(value.items()):
            child = QTreeWidgetItem()
            # val is dict or a list -> recurse
            if hasattr(val, 'items') or _listlike(val):
                child.setText(0, _short_repr(key).strip("'"))
                item.addChild(child)
                fill_item(child, val)
                if key == 'descriptors':
                    child.setExpanded(False)
            # val is not iterable -> show key and val on one line
            else:
                # Show human-readable datetime alongside raw timestamp.
                # 1484948553.567529 > '[2017-01-20 16:42:33] 1484948553.567529'
                if (key == 'time') and isinstance(val, float):
                    FMT = '%Y-%m-%d %H:%M:%S'
                    ts = datetime.fromtimestamp(val).strftime(FMT)
                    text = "time: [{}] {}".format(ts, val)
                else:
                    text = "{}: {}".format(_short_repr(key).strip("'"),
                                           _short_repr(val))
                child.setText(0, text)
                item.addChild(child)

    elif type(value) is list:
        for val in value:
            if hasattr(val, 'items'):
                fill_item(item, val)
            elif _listlike(val):
                fill_item(item, val)
            else:
                child = QTreeWidgetItem()
                item.addChild(child)
                child.setExpanded(False)
                child.setText(0, _short_repr(val))
    else:
        child = QTreeWidgetItem()
        child.setText(0, _short_repr(value))
        item.addChild(child)


def _listlike(val):
    return isinstance(val, Iterable) and not isinstance(val, str)


def _short_repr(text):
    r = repr(text)
    if len(r) > 82:
        r = r[:27] + '...'
    return r


class HeaderTreeWidget(QTreeWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAlternatingRowColors(True)
        self.setHeaderHidden(True)

    def __call__(self, name, doc):
        fill_item(self.invisibleRootItem(), {name: doc})
        return []


class HeaderTreeFactory:
    def __init__(self, add_tab):
        container = QWidget()
        self.layout = QVBoxLayout()
        container.setLayout(self.layout)
        add_tab(container, 'Header')

    def __call__(self, name, start_doc):
        """
        Make a HeaderTreeWidget and give it the start and descriptor and stop docs.
        """
        header_tree_widget = HeaderTreeWidget()
        self.layout.addWidget(header_tree_widget)
        header_tree_widget('start', start_doc)

        def get_stop(name, doc):
            if name == 'stop':
                header_tree_widget('stop', doc)

        def subfactory(name, descriptor_doc):
            header_tree_widget('descriptor', descriptor_doc)
            return []

        return [get_stop], [subfactory]
