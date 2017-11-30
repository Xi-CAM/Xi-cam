from astropy.modeling import Fittable1DModel
from yapsy.IPlugin import IPlugin


class Fittable1DModelPlugin(Fittable1DModel, IPlugin):
    """
    Plugins of this base class mimic the astropy FittableModel class structure. An activated fittable model would be
    usable for fitting 1-d spectra or 2-d images. Example: A 1-D Lorentzian model, usable for fitting SAXS spectra.

    See the Astropy API for a detailed explanation of the usage.

    See xicam.plugins.tests for examples.

    """

    @staticmethod
    def evaluate(x, *args, **kwargs):
        raise NotImplementedError

    @staticmethod
    def fit_deriv(x, *args, **kwargs):
        raise NotImplementedError

    @property
    def inverse(self):
        raise NotImplementedError

        # TODO: add fitting convenience method
