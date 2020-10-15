import time

import event_model
from pytest import fixture
import scipy.misc

from xicam.core.data.bluesky_utils import run_from_doc_stream


def synthetic_ingestor():
    timestamp = time.time()
    run_bundle = event_model.compose_run()
    data = scipy.misc.face(True)
    field = "some_data"
    source = "synthetic_ingestor"
    frame_data_keys = {field: {"source": source, "dtype": "number", "shape": data.shape}}
    frame_stream_name = "primary"
    frame_stream_bundle = run_bundle.compose_descriptor(data_keys=frame_data_keys, name=frame_stream_name)
    yield "start", run_bundle.start_doc
    yield "descriptor", frame_stream_bundle.descriptor_doc
    yield "event", frame_stream_bundle.compose_event(data={field: data}, timestamps={field: timestamp})
    yield "stop", run_bundle.compose_stop()


@fixture
def catalog():
    return run_from_doc_stream(synthetic_ingestor())
