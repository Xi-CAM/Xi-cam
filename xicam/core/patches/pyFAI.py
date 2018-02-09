import pyFAI
import numpy

import logging

logger = logging.getLogger("pyFAI.azimuthalIntegrator")


class Detector(pyFAI.Detector):
    __statevars = (
        '_pixel1', '_pixel2', '_pixel_corners', '_binning', '_mask', '_mask_crc', '_maskfile', '_splineFile', '_dx',
        '_dy',
        '_flatfield', '_flatfield_crc', '_darkcurrent', '_darkcurrent_crc', '_splineCache', 'shape')

    def __getnewargs_ex__(self):
        return ((self.pixel1, self.pixel2, self.splineFile, self.max_shape), {})

    def __getstate__(self):
        vars = self.__statevars
        return tuple(getattr(self, var) for var in vars)

    def __setstate__(self, state):
        for statevar, varkey in zip(state, self.__statevars):
            setattr(self, varkey, statevar)
        self.engines = {}


# monkey patch to correct auto-inversion of masks when 'numpy' is used
class AzimuthalIntegrator(pyFAI.AzimuthalIntegrator):
    def create_mask(self, data, mask=None,
                    dummy=None, delta_dummy=None, mode="normal"):
        """
        Combines various masks into another one.

        @param data: input array of data
        @type data: ndarray
        @param mask: input mask (if none, self.mask is used)
        @type mask: ndarray
        @param dummy: value of dead pixels
        @type dummy: float
        @param delta_dumy: precision of dummy pixels
        @type delta_dummy: float
        @param mode: can be "normal" or "numpy" (inverted) or "where" applied to the mask
        @type mode: str

        @return: the new mask
        @rtype: ndarray of bool

        This method combine two masks (dynamic mask from *data &
        dummy* and *mask*) to generate a new one with the 'or' binary
        operation.  One can adjust the level, with the *dummy* and
        the *delta_dummy* parameter, when you consider the *data*
        values needs to be masked out.

        This method can work in two different *mode*:

            * "normal": False for valid pixels, True for bad pixels
            * "numpy": True for valid pixels, false for others

        This method tries to accomodate various types of masks (like
        valid=0 & masked=-1, ...) and guesses if an input mask needs
        to be inverted.
        """
        shape = data.shape
        #       ^^^^   this is why data is mandatory !
        if mask is None:
            mask = self.mask
        if mask is None:
            mask = numpy.zeros(shape, dtype=bool)
        elif mask.min() < 0 and mask.max() == 0:  # 0 is valid, <0 is invalid
            mask = (mask < 0)
        else:
            mask = mask.astype(bool)
        # if mask.sum(dtype=int) > mask.size // 2:                              # TERRRIBLEE!
        #     logger.warning("Mask likely to be inverted as more"
        #                    " than half pixel are masked !!!")
        #     numpy.logical_not(mask, mask)
        if (mask.shape != shape):
            try:
                mask = mask[:shape[0], :shape[1]]
            except Exception as error:  # IGNORE:W0703
                logger.error("Mask provided has wrong shape:"
                             " expected: %s, got %s, error: %s" %
                             (shape, mask.shape, error))
                mask = numpy.zeros(shape, dtype=bool)
        if dummy is not None:
            if delta_dummy is None:
                numpy.logical_or(mask, (data == dummy), mask)
            else:
                numpy.logical_or(mask,
                                 abs(data - dummy) <= delta_dummy,
                                 mask)
        if mode == "numpy":
            numpy.logical_not(mask, mask)
        elif mode == "where":
            mask = numpy.where(numpy.logical_not(mask))
        return mask

    __statevars = (
        '_cached_array', '_dssa', '_dssa_crc', '_dssa_order', '_oversampling', '_correct_solid_angle_for_spline',
        '_cosa',
        '_transmission_normal', '_transmission_corr', '_transmission_crc', 'detector')

    def __getnewargs_ex__(self):
        return ((self.dist, self.poni1, self.poni2, self.rot1, self.rot2, self.rot3, self.pixel1, self.pixel2,
                 self.splineFile, self.detector, self.wavelength), {})

    def __getstate__(self):
        vars = self.__statevars
        return tuple(getattr(self, var) for var in vars)

    def __setstate__(self, state):
        for statevar, varkey in zip(state, self.__statevars):
            setattr(self, varkey, statevar)
        self.engines = {}


pyFAI.__dict__['AzimuthalIntegrator'] = AzimuthalIntegrator

new_ALL_DETECTORS = {}
new_ALL_DETECTORS['Detector'] = pyFAI.detectors.__dict__['Detector'] = pyFAI.__dict__['Detector'] = Detector

for name, detector in pyFAI.detectors.ALL_DETECTORS.items():
    if name != 'detector':
        new_ALL_DETECTORS['name'] = type(detector.__name__, tuple(
            base for base in detector.__bases__ if not base.__name__ == 'Detector') + (Detector,),
                                         dict(detector.__dict__))
