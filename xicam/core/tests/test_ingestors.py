import tempfile
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image

from xicam.core.ingestors import generic


class TestGeneric:

    def test_tiff(self):
        # Write a small TIFF file
        test_data, _, _ = np.mgrid[0:30, 0:40, 0:50]
        test_data = test_data.astype("<u2")

        tmp = tempfile.TemporaryDirectory()
        file_path = Path(tmp.name) / Path("temp_tif.tif")
        tifffile.imsave(
            file_path, test_data, imagej=True, resolution=(0.2, 0.2), metadata={"unit": "um"}
        )

        # TODO test metadata

        # Make sure we generated a valid doc
        docs = list(generic.ingest([str(file_path)]))
        assert len(docs) == 4
        expected_keys = ["start", "descriptor", "event", "stop"]
        for i, doc in enumerate(docs):
            assert doc[0] == expected_keys[i]

        # Try to read the event data
        dask_array = docs[2][1]["data"]["raw"]  # type: dask.array
        event_data = dask_array.compute()
        assert np.array_equal(event_data, test_data)


    def test_jpeg(self):
        # Create a test image
        image = Image.new("L", (10, 20), color=100)
        tmp = tempfile.TemporaryDirectory()
        file_path = Path(tmp.name) / Path("temp_jpeg.jpeg")
        image.save(file_path)

        # Ingest
        docs = list(generic.ingest([str(file_path)]))

        # Check that the document is valid
        assert len(docs) == 4
        expected_keys = ["start", "descriptor", "event", "stop"]
        for i, _ in enumerate(docs):
            assert docs[i][0] == expected_keys[i]

        # Try to read the event data
        dask_array = docs[2][1]["data"]["raw"]  # type: dask.array
        event_data = dask_array.compute()
        # The ingestor does a dask_array.stack, so we need to squeeze off the extra dimension
        assert np.array_equal(event_data.squeeze(), np.asarray(image))
