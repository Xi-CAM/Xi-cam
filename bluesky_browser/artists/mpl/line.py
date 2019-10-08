import collections

from event_model import DocumentRouter
import matplotlib.pyplot as plt


class Line(DocumentRouter):
    """
    Draw a matplotlib Line Arist update it for each Event.

    Parameters
    ----------
    func : callable
        This must accept an EventPage and return two lists of floats
        (x points and y points). The two lists must contain an equal number of
        items, but that number is arbitrary. That is, a given document may add
        one new point to the plot, no new points, or multiple new points.
    label_template : string
        This string will be formatted with the RunStart document. Any missing
        values will be filled with '?'. If the keyword argument 'label' is
        given, this argument will be ignored.
    ax : matplotlib Axes, optional
        If None, a new Figure and Axes are created.
    **kwargs
        Passed through to :meth:`Axes.plot` to style Line object.
    """
    def __init__(self, func, *, label_template='{scan_id} [{uid:.8}]', ax=None, **kwargs):
        self.func = func
        if ax is None:
            _, ax = plt.subplots()
        self.ax = ax
        self.line, = ax.plot([], [], **kwargs)
        self.x_data = []
        self.y_data = []
        self.label_template = label_template
        self.label = kwargs.get('label')

    def start(self, doc):
        if self.label is None:
            d = collections.defaultdict(lambda: '?')
            d.update(**doc)
            label = self.label_template.format_map(d)
        else:
            label = self.label
        if label:
            self.line.set_label(label)
            self.ax.legend(loc='best')

    def event_page(self, doc):
        x, y = self.func(doc)
        self._update(x, y)

    def _update(self, x, y):
        """
        Takes in new x and y points and redraws plot if they are not empty.
        """
        if not len(x) == len(y):
            raise ValueError("User function is expected to provide the same "
                             "number of x and y points. Got {len(x)} x points "
                             "and {len(y)} y points.")
        if not x:
            # No new data. Short-circuit.
            return
        self.x_data.extend(x)
        self.y_data.extend(y)
        self.line.set_data(self.x_data, self.y_data)
        self.ax.relim(visible_only=True)
        self.ax.autoscale_view(tight=True)
        self.ax.figure.canvas.draw_idle()
