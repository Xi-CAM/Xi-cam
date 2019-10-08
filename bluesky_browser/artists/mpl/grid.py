from event_model import DocumentRouter
import matplotlib.pyplot as plt
import numpy


class Grid(DocumentRouter):
    """
    Draw a matplotlib AxesImage Arist update it for each Event.

    The purposes of this callback is to create (on initialization) of a
    matplotlib grid image and then update it with new data for every `event`.
    NOTE: Some important parameters are fed in through **kwargs like `extent`
    which defines the axes min and max and `origin` which defines if the grid
    co-ordinates start in the bottom left or top left of the plot. For more
    info see https://matplotlib.org/tutorials/intermediate/imshow_extent.html
    or https://matplotlib.org/api/_as_gen/matplotlib.axes.Axes.imshow.html#matplotlib.axes.Axes.imshow

    Parameters
    ----------
    func : callable
        This must accept a BulkEvent and return three lists of floats (x
        grid co-ordinates, y grid co-ordinates and grid position intensity
        values). The three lists must contain an equal number of items, but
        that number is arbitrary. That is, a given document may add one new
        point, no new points or multiple new points to the plot.
    shape : tuple
        The (row, col) shape of the grid.
    ax : matplotlib Axes, optional.
        if ``None``, a new Figure and Axes are created.
    **kwargs
        Passed through to :meth:`Axes.imshow` to style the AxesImage object.
    """
    def __init__(self, func, shape, *, ax=None, **kwargs):
        self.func = func
        self.shape = shape
        if ax is None:
            _, ax = plt.subplots()
        self.ax = ax
        self.grid_data = numpy.full(self.shape, numpy.nan)
        self.image, = ax.imshow(self.grid_data, **kwargs)

    def event_page(self, doc):
        '''
        Takes in a bulk_events document and updates grid_data with the values
        returned from self.func(doc)

        Parameters
        ----------
        doc : dict
            The bulk event dictionary that contains the 'data' and 'timestamps'
            associated with the bulk event.

        Returns
        -------
        x_coords, y_coords, I_vals : Lists
            These are lists of x co-ordinate, y co-ordinate and intensity
            values arising from the bulk event.
        '''
        x_coords, y_coords, I_vals = self.func(doc)
        self._update(x_coords, y_coords, I_vals)

    def _update(self, x_coords, y_coords, I_vals):
        '''
        Updates self.grid_data with the values from the lists x_coords,
        y_coords, I_vals.

        Parameters
        ----------
        x_coords, y_coords, I_vals : Lists
            These are lists of x co-ordinate, y co-ordinate and intensity
            values arising from the event. The length of all three lists must
            be the same.
        '''

        if not len(x_coords) == len(y_coords) == len(I_vals):
            raise ValueError("User function is expected to provide the same "
                             "number of x, y and I points. Got {0} x points, "
                             "{1} y points and {2} I values."
                             "".format(len(x_coords), len(y_coords),
                                       len(I_vals)))

        if not x_coords:
            # No new data, Short-circuit.
            return

        # Update grid_data and the plot.
        self.grid_data[x_coords, y_coords] = I_vals
        self.image.set_array(self.grid_data)
