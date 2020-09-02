from xarray import Dataset


class Intent:
    def __init__(self, name="", category=""):
        self._name = name
        # self._category = category

    @property
    def name(self):
        return self._name

    # # TODO : WIP (this is not part of an intent inherently yet, just testing)
    # @property
    # def category(self):
    #     return self._category


# class MatplotlibImageCanvas(ImageIntentCanvas):
#     def render(self, ...):
#         matplotlib.imshow(...)


class ImageIntent(Intent):
    canvas = {"qt": "image_canvas"}

    def __init__(self, image, *args, **kwargs):
        super(ImageIntent, self).__init__(*args, **kwargs)
        self.image = image


class PlotIntent(Intent):
    canvas = {"qt": "plot_canvas"}

    def __init__(self, x: Dataset, y: Dataset, *args, **kwargs):
        super(PlotIntent, self).__init__(*args, **kwargs)
        self.x = x
        self.y = y

    @property
    def name(self):
        return self.x.name + ", " + self.y.name
