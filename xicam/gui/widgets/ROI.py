from pyqtgraph import ROI, PolyLineROI
from pyqtgraph.graphicsItems.ROI import Handle


# MIXIN!~
# Now with 100% more ROI!
class BetterROI(ROI):
    roi_count = 0
    index = None

    def __new__(cls, *args, **kwargs):
        BetterROI.roi_count += 1
        instance = ROI.__new__(cls, *args, **kwargs)
        instance.index = cls.roi_count
        return instance

    def __init__(self, *args, **kwargs):
        super(BetterROI, self).__init__(*args, **kwargs)

        for handledict in self.handles:  # type: dict
            handle = handledict["item"]  # type: Handle
            handle.radius = handle.radius * 2
            handle.buildPath()


class BetterPolyLineROI(BetterROI, PolyLineROI):
    def __repr__(self):
        return f"ROI #{self.index}"
