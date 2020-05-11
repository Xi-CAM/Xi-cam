# FittableModelPlugin
Plugins of this base class mimic the astropy FittableModel class structure. An activated fittable model would be usable for fitting 1-d spectra or 2-d images. Example: A 1-D Lorentzian model, usable for fitting SAXS spectra.
See the Astropy API for a detailed explanation of the usage.
## Methods
The plugin allows to implement the three following methods. While it is enough to implement ```evaluate``` for fitting implementing the other methods aids the fitting algorithm.
### evaluate
A method, that allows evaluation of the model function
### fit_deriv
A method, that returns the derivatives of the model function
### inverse
A method returning the inverse of the model function
## Example Implementation
An easy example of such a model would be a simple one dimensional gaussian. A valid implementation of which can be found below.
```python
import numpy as np
from astropy.modeling import Parameter
from xicam.plugins.FittableModelPlugin import Fittable1DModelPlugin

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
```
This example from AstroPy. Gaussian1D is already a member of astropy's models
