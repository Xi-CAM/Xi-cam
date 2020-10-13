from xicam.core.intents import ImageIntent
from xicam.plugins.operationplugin import operation, output_names, display_name, describe_input, describe_output, \
    categories, intent, visible
import numpy as np
import scipy.misc
import scipy.fft




#region "Easy"-difficulty wrapping
# random_array = operation(np.random.random)
#endregion

# region "Medium"-difficulty wrapping
@operation
@output_names("data")
@display_name("Random Array")
@categories(("General", "Mathematics"))
def random_array(rows: int = 10, columns: int = 10) -> np.ndarray:
    return np.random.random((rows, columns))


@operation
@output_names("data")
@display_name("Raccoon Face")
@categories(("General", "Synthetic Data"))
@intent(ImageIntent, 'Raccoon Face', output_map={'image': 'data'})
def raccoon_face(gray: bool = True) -> np.ndarray:
    return scipy.misc.face(gray=gray)


@operation
@output_names("spectral_data")
@display_name("Fourier Transform")
@categories(("General", "Mathematics"))
@intent(ImageIntent, 'Fourier Transform', output_map={'image': 'spectral_data'})
@visible('data', False)
def fourier_transform(data: np.ndarray) -> np.ndarray:
    return scipy.fft.fft2(data)


@operation
@output_names("spectral_data")
@display_name("Low Band Pass Filter")
@intent(ImageIntent, 'Low Band Pass Filter', output_map={'image': 'spectral_data'})
@categories(("General", "Mathematics"))
@visible('spectral_data', False)
def low_band_pass(spectral_data: np.ndarray, keep_fraction:float=.1)->np.ndarray:
    shape = spectral_data.shape

    # Set to zero all rows with indices between r*keep_fraction and shape[0]*(1-keep_fraction):
    spectral_data[int(shape[0] * keep_fraction):int(shape[0] * (1 - keep_fraction))] = 0

    # Similarly with the columns:
    spectral_data[:, int(shape[1] * keep_fraction):int(shape[1] * (1 - keep_fraction))] = 0

    return spectral_data


@operation
@output_names("spectral_data")
@display_name("Absolute Square")
@categories(("General", "Mathematics"))
@visible('spectral_data', False)
@intent(ImageIntent, 'Absolute Square', output_map={'image': 'spectral_data'})
def absolute_square(spectral_data: np.ndarray) -> np.ndarray:
    return np.square(np.abs(spectral_data))


@operation
@output_names("data")
@display_name("Inverse Fourier Transform")
@categories(("General", "Mathematics"))
@visible('spectral_data', False)
@intent(ImageIntent, 'Inverse Fourier Transform', output_map={'image': 'data'})
def inverse_fourier_transform(spectral_data: np.ndarray) -> np.ndarray:
    return scipy.fft.ifft2(spectral_data)
