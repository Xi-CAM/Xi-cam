from xicam.core.patches.pyFAI import *


def test_Detector_pickle():
    import cloudpickle
    import numpy as np
    from pyFAI import Detector
    det = Detector.factory('pilatus2m')

    print(det, type(det))

    # print(det.__reduce__())
    # print(det.__getnewargs_ex__())
    # print(det.__getstate__())

    assert cloudpickle.dumps(det)
    assert cloudpickle.loads(cloudpickle.dumps(det))


def test_AzimuthalIntegrator_pickle():
    import cloudpickle
    import numpy as np

    det = pyFAI.detectors.detector_factory('pilatus2m')
    ai = AzimuthalIntegrator(detector=det)
    ai.set_wavelength(.1)
    spectra = ai.integrate1d(np.ones(det.shape), 1000)  # force lut generation
    dump = cloudpickle.dumps(ai)
    newai = cloudpickle.loads(dump)
    assert np.array_equal(newai.integrate1d(np.ones(det.shape), 1000), spectra)
