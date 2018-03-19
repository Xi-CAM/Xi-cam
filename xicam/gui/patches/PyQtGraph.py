'''
This patch module adds color gradients like matplotlib's viridis etc. to PyQtGraph
'''
from pyqtgraph.graphicsItems import GradientEditorItem
from collections import OrderedDict
from qtpy.QtWidgets import QTreeWidgetItem

GradientEditorItem.__dict__['Gradients'] = OrderedDict([
    ('thermal', {'ticks': [(0.3333, (185, 0, 0, 255)), (0.6666, (255, 220, 0, 255)), (1, (255, 255, 255, 255)), (0, (0, 0, 0, 255))], 'mode': 'rgb'}),
    ('flame', {'ticks': [(0.2, (7, 0, 220, 255)), (0.5, (236, 0, 134, 255)), (0.8, (246, 246, 0, 255)), (1.0, (255, 255, 255, 255)), (0.0, (0, 0, 0, 255))], 'mode': 'rgb'}),
    ('yellowy', {'ticks': [(0.0, (0, 0, 0, 255)), (0.2328863796753704, (32, 0, 129, 255)), (0.8362738179251941, (255, 255, 0, 255)), (0.5257586450247, (115, 15, 255, 255)), (1.0, (255, 255, 255, 255))], 'mode': 'rgb'} ),
    ('bipolar', {'ticks': [(0.0, (0, 255, 255, 255)), (1.0, (255, 255, 0, 255)), (0.5, (0, 0, 0, 255)), (0.25, (0, 0, 255, 255)), (0.75, (255, 0, 0, 255))], 'mode': 'rgb'}),
    ('viridis', {'ticks': [(0.0, (68, 1, 84, 255)), (0.25, (58, 82, 139, 255)), (0.5, (32, 144, 140, 255)), (0.75, (94, 201, 97, 255)), (1.0, (253, 231, 36, 255))], 'mode': 'rgb'}),
    ('inferno', {'ticks': [(0.0, (0, 0, 3, 255)), (0.25, (87, 15, 109, 255)), (0.5, (187, 55, 84, 255)), (0.75, (249, 142, 8, 255)), (1.0, (252, 254, 164, 255))], 'mode': 'rgb'}),
    ('plasma', {'ticks': [(0.0, (12, 7, 134, 255)), (0.25, (126, 3, 167, 255)), (0.5, (203, 71, 119, 255)), (0.75, (248, 149, 64, 255)), (1.0, (239, 248, 33, 255))], 'mode': 'rgb'}),
    ('magma', {'ticks': [(0.0, (0, 0, 3, 255)), (0.25, (80, 18, 123, 255)), (0.5, (182, 54, 121, 255)), (0.75, (251, 136, 97, 255)), (1.0, (251, 252, 191, 255))], 'mode': 'rgb'}),
    ('spectrum', {'ticks': [(1.0, (255, 0, 255, 255)), (0.0, (255, 0, 0, 255))], 'mode': 'hsv'}),
    ('cyclic', {'ticks': [(0.0, (255, 0, 4, 255)), (1.0, (255, 0, 0, 255))], 'mode': 'hsv'}),
    ('greyclip', {'ticks': [(0.0, (0, 0, 0, 255)), (0.99, (255, 255, 255, 255)), (1.0, (255, 0, 0, 255))], 'mode': 'rgb'}),
    ('grey', {'ticks': [(0.0, (0, 0, 0, 255)), (1.0, (255, 255, 255, 255))], 'mode': 'rgb'}),
])

from pyqtgraph.parametertree import Parameter, ParameterItem, registerParameterType
from pyqtgraph.parametertree.parameterTypes import WidgetParameterItem
from pyqtgraph import ImageView
import numpy as np


class ImageParameterItem(WidgetParameterItem):
    def makeWidget(self):
        self.subItem = QTreeWidgetItem()
        self.addChild(self.subItem)

        w = ImageView()
        w.value = lambda: w.image
        w.setValue = lambda image: w.setImage(np.squeeze(image))
        w.sigChanged = None

        self.hideWidget = False
        return w

    def treeWidgetChanged(self):
        ## TODO: fix so that superclass method can be called
        ## (WidgetParameter should just natively support this style)
        # WidgetParameterItem.treeWidgetChanged(self)
        self.treeWidget().setFirstItemColumnSpanned(self.subItem, True)
        self.treeWidget().setItemWidget(self.subItem, 0, self.widget)

        # for now, these are copied from ParameterItem.treeWidgetChanged
        self.setHidden(not self.param.opts.get('visible', True))
        self.setExpanded(self.param.opts.get('expanded', True))

    def valueChanged(self, param, val, force=False):
        ## called when the parameter's value has changed
        ParameterItem.valueChanged(self, param, val)
        if force or not np.array_equal(val, self.widget.value()):
            self.widget.setValue(val.astype(np.float))
        self.updateDisplayLabel(val)  ## always make sure label is updated, even if values match!

    def updateDefaultBtn(self):
        pass


class ImageParameter(Parameter):
    itemClass = ImageParameterItem

    def __init__(self, *args, **kwargs):
        if 'expanded' not in kwargs: kwargs['expanded'] = False
        super(ImageParameter, self).__init__(*args, **kwargs)

    def setValue(self, value, blockSignal=None):
        """
        Set the value of this Parameter; return the actual value that was set.
        (this may be different from the value that was requested)
        """
        try:
            if blockSignal is not None:
                self.sigValueChanged.disconnect(blockSignal)
            if np.array_equal(self.opts['value'], value):
                return value
            self.opts['value'] = value
            # self.sigValueChanged.emit(self, value)
        finally:
            if blockSignal is not None:
                self.sigValueChanged.connect(blockSignal)

        return value


registerParameterType('ndarray', ImageParameter, override=True)
