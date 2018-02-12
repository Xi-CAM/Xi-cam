from xicam.core.execution.workflow import Workflow
from xicam.core.execution.daskexecutor import DaskExecutor

from xicam.plugins import Input, Output, ProcessingPlugin

from pyFAI.detectors import Pilatus2M
import numpy as np
from pyFAI import AzimuthalIntegrator, units
from scipy.ndimage import morphology
import fabio


class ThresholdMaskPlugin(ProcessingPlugin):
    data = Input(description='Frame image data',
                 type=np.ndarray)
    minimum = Input(description='Threshold floor',
                    type=int)
    maximum = Input(description='Threshold ceiling',
                    type=int)
    neighborhood = Input(
        description='Neighborhood size in pixels for morphological opening. Only clusters of this size'
                    ' that fail the threshold are masked',
        type=int)
    mask = Output(description='Thresholded mask (1 is masked)',
                  type=np.ndarray)

    def evaluate(self):
        self.mask.value = np.logical_or(self.data.value < self.minimum.value, self.data.value > self.maximum.value)

        y, x = np.ogrid[-self.neighborhood.value:self.neighborhood.value + 1,
               -self.neighborhood.value:self.neighborhood.value + 1]
        kernel = x ** 2 + y ** 2 <= self.neighborhood.value ** 2

        morphology.binary_opening(self.mask.value, kernel, output=self.mask.value)  # write-back to mask


class QIntegratePlugin(ProcessingPlugin):
    integrator = Input(description='A PyFAI.AzimuthalIntegrator object',
                       type=AzimuthalIntegrator)
    data = Input(description='2d array representing intensity for each pixel',
                 type=np.ndarray)
    npt = Input(description='Number of bins along q')
    polz_factor = Input(description='Polarization factor for correction',
                        type=float)
    unit = Input(description='Output units for q',
                 type=[str, units.Unit],
                 default="q_A^-1")
    radial_range = Input(
        description='The lower and upper range of the radial unit. If not provided, range is simply '
                    '(data.min(), data.max()). Values outside the range are ignored.',
        type=tuple)
    azimuth_range = Input(
        description='The lower and upper range of the azimuthal angle in degree. If not provided, '
                    'range is simply (data.min(), data.max()). Values outside the range are ignored.')
    mask = Input(description='Array (same size as image) with 1 for masked pixels, and 0 for valid pixels',
                 type=np.ndarray)
    dark = Input(description='Dark noise image',
                 type=np.ndarray)
    flat = Input(description='Flat field image',
                 type=np.ndarray)
    method = Input(description='Can be "numpy", "cython", "BBox" or "splitpixel", "lut", "csr", "nosplit_csr", '
                               '"full_csr", "lut_ocl" and "csr_ocl" if you want to go on GPU. To Specify the device: '
                               '"csr_ocl_1,2"',
                   type=str)
    normalization_factor = Input(description='Value of a normalization monitor',
                                 type=float)
    q = Output(description='Q bin center positions',
               type=np.array)
    I = Output(description='Binned/pixel-split integrated intensity',
               type=np.array)

    def evaluate(self):
        self.q.value, self.I.value = self.integrator.value().integrate1d(data=self.data.value,
                                                                       npt=self.npt.value,
                                                                       radial_range=self.radial_range.value,
                                                                       azimuth_range=self.azimuth_range.value,
                                                                       mask=self.mask.value,
                                                                       polarization_factor=self.polz_factor.value,
                                                                       dark=self.dark.value,
                                                                       flat=self.flat.value,
                                                                       method=self.method.value,
                                                                       unit=self.unit.value,
                                                                       normalization_factor=self.normalization_factor.value)


def test_SAXSWorkflow():
    # create processes
    thresholdmask = ThresholdMaskPlugin()
    qintegrate = QIntegratePlugin()

    # set values
    AI = AzimuthalIntegrator(.283, 5.24e-3, 4.085e-3, 0, 0, 0, 1.72e-4, 1.72e-4, detector=Pilatus2M(),
                             wavelength=1.23984e-10)
    thresholdmask.data.value = fabio.open('/Users/hari/Downloads/AGB_5S_USE_2_2m.edf').data

    def AI_func():
        from pyFAI.detectors import Pilatus2M
        from pyFAI import AzimuthalIntegrator, units
        return AzimuthalIntegrator(.283, 5.24e-3, 4.085e-3, 0, 0, 0, 1.72e-4, 1.72e-4, detector=Pilatus2M(),
                                   wavelength=1.23984e-10)

    qintegrate.integrator.value = AI_func
    qintegrate.npt.value = 1000
    thresholdmask.minimum.value = 30
    thresholdmask.maximum.value = 1e12

    qintegrate.data.value = fabio.open('/Users/hari/Downloads/AGB_5S_USE_2_2m.edf').data
    thresholdmask.neighborhood.value = 1
    qintegrate.normalization_factor.value = 0.5
    qintegrate.method.value = "numpy"

    # connect processes
    thresholdmask.mask.connect(qintegrate.mask)

    # add processes to workflow
    wf = Workflow('QIntegrate')
    wf.addProcess(thresholdmask)
    wf.addProcess(qintegrate)

    dsk = DaskExecutor()
    result = dsk.execute(wf)
    print(result)



def test_autoconnect():
    # create processes
    thresholdmask = ThresholdMaskPlugin()
    qintegrate = QIntegratePlugin()

    # set values
    AI = AzimuthalIntegrator(.283, 5.24e-3, 4.085e-3, 0, 0, 0, 1.72e-4, 1.72e-4, detector=Pilatus2M(),
                             wavelength=1.23984e-10)
    thresholdmask.data.value = fabio.open('/Users/hari/Downloads/AGB_5S_USE_2_2m.edf').data
    qintegrate.integrator.value = AI
    qintegrate.npt.value = 1000
    thresholdmask.minimum.value = 30
    thresholdmask.maximum.value = 1e12

    # add process to workflow
