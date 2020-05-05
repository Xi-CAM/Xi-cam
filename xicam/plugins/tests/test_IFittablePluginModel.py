import pytest
from pytestqt import qtbot

def test_IFittableModelPlugin(qtbot):
    from ..fittablemodelplugin import Fittable1DModelPlugin
    import numpy as np
    from astropy.modeling.fitting import LevMarLSQFitter
    from astropy.modeling import Parameter

    # Below example copied from AstroPy for demonstration; Gaussian1D is already a member of astropy's models
    class Gaussian1D(Fittable1DModelPlugin):
        amplitude = Parameter("amplitude")
        mean = Parameter("mean")
        stddev = Parameter("stddev")

        @staticmethod
        def evaluate(x, amplitude, mean, stddev):
            """
            Gaussian1D model function.
            """
            return amplitude * np.exp(-0.5 * (x - mean) ** 2 / stddev ** 2)

        @staticmethod
        def fit_deriv(x, amplitude, mean, stddev):
            """
            Gaussian1D model function derivatives.
            """

            d_amplitude = np.exp(-0.5 / stddev ** 2 * (x - mean) ** 2)
            d_mean = amplitude * d_amplitude * (x - mean) / stddev ** 2
            d_stddev = amplitude * d_amplitude * (x - mean) ** 2 / stddev ** 3
            return [d_amplitude, d_mean, d_stddev]

    # Generate fake data
    np.random.seed(0)
    x = np.linspace(-5.0, 5.0, 200)
    m_ref = Gaussian1D(amplitude=2.0, mean=1, stddev=3)
    from astropy.modeling.models import Gaussian1D

    Gaussian1D()(x)
    y = m_ref(x) + np.random.normal(0.0, 0.1, x.shape)

    # Fit model to data
    m_init = Gaussian1D()

    fit = LevMarLSQFitter()
    m = fit(m_init, x, y)

    assert round(m.amplitude.value) == 2
    assert round(m.mean.value) == 1
    assert round(m.stddev.value) == 3
