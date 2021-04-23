from qtpy.QtCore import QEvent
from pyqtgraph import ROI


class Action(QEvent):
    def __init__(self, event_type=QEvent.User):
        super(Action, self).__init__(event_type)
        self.ignore()


class ROIAction(Action):
    def __init__(self, roi: ROI, event_type=QEvent.User):
        super(ROIAction, self).__init__(event_type)
        self.roi = roi
