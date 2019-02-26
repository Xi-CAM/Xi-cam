from pyqtgraph import ROI, PolyLineROI
from pyqtgraph.graphicsItems.ROI import Handle


# MIXIN!~
# Now with 100% more ROI!
class BetterROI(ROI):
    def __init__(self, *args, **kwargs):
        super(BetterROI, self).__init__(*args, **kwargs)

        #
        for handledict in self.handles:  # type: dict
            handle = handledict['item']  # type: Handle
            handle.radius = handle.radius * 2
            handle.buildPath()


class BetterPolyLineROI(BetterROI, PolyLineROI):
    pass
