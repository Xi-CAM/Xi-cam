"""Generic ingestion of raw images using the fabIO package.

Current registered formats can be found under the 'databroker.ingestors' entry point
in xicam's setup.py.
"""
import time

import dask.array as da
import event_model
import fabio


def _get_slice(image, frame):
    return image.get_frame(frame).data


def ingest(paths):
    """Ingest a generic image file.

    Can be used to load any formats that FabIO can read.

    Parameters
    ----------
    paths: List
        List of file paths to ingest. Note that only a single path is currently supported.
    """
    assert len(paths) == 1
    path = paths[0]
    image = fabio.open(path)  # type: fabio.fabioimage.FabioImage

    # Create a BlueskyRun
    run_bundle = event_model.compose_run()

    # Create the start document
    start_doc = run_bundle.start_doc
    start_doc["sample_name"] = image.filename
    yield "start", start_doc

    # Create the descriptor document - defines the data keys
    source = image.header.get("source", "Local")
    frame_data_keys = {
        "raw": {"source": source, "dtype": "number", "shape": (image.nframes, *image.shape)}
    }
    frame_stream_name = "primary"
    frame_stream_bundle = run_bundle.compose_descriptor(
        data_keys=frame_data_keys, name=frame_stream_name
    )
    yield "descriptor", frame_stream_bundle.descriptor_doc

    # Create the event document - contains the data
    # delayed_get_slice = dask.delayed(_get_slice)
    # dask_data = da.stack(
    #     [da.from_delayed(delayed_get_slice(image, frame), shape=image.shape, dtype=image.dtype)
    #     for frame in range(image.nframes)]
    # )
    dask_data = da.stack([frame.data for frame in image.frames()])
    timestamp = image.header.get("time", time.time())
    yield "event", frame_stream_bundle.compose_event(
        data={"raw": dask_data}, timestamps={"raw": timestamp}
    )

    # Create the stop document
    yield "stop", run_bundle.compose_stop()


if __name__ == "__main__":
    from pathlib import Path
    import numpy as np
    import tempfile
    import tifffile

    # Write a small TIF file
    dd, _, _ = np.mgrid[0:30, 0:40, 0:50]
    dd = dd.astype("<u2")

    tmp = tempfile.TemporaryDirectory()
    fPath = Path(tmp.name) / Path("temp_tif.tif")
    tifffile.imsave(fPath, dd, imagej=True, resolution=(0.2, 0.2), metadata={"unit": "um"})
    docs = list(ingest([str(fPath)]))
    print(docs)
