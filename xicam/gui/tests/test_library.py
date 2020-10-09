import time
from typing import List, Generator, Tuple
import numpy as np
from pytest import fixture
import pytest
from _pytest.fixtures import SubRequest
from pytestqt import qtbot
import event_model
from databroker.in_memory import BlueskyInMemoryCatalog
from xicam.gui.widgets.library import LibraryWidget, LibraryView
from qtpy.QtWidgets import QWidget, QHBoxLayout, QSlider
from functools import partial

DATA_SHAPE = (100, 100)
FRAMES = 100


def doc_stream(streams: List[str], fields: List[str], frames: int) -> Generator[Tuple[str, dict], None, None]:
    def doc_gen(stream_names):

        # Compose run start
        run_bundle = event_model.compose_run()  # type: event_model.ComposeRunBundle
        start_doc = run_bundle.start_doc

        yield 'start', start_doc

        for stream_name in stream_names:

            # Compose descriptor
            source = 'synthetic'
            frame_data_keys = {field: {'source': source,
                                       'dtype': 'number',
                                       'dims': ('x', 'y'),
                                       'shape': DATA_SHAPE} for field in fields}
            frame_stream_bundle = run_bundle.compose_descriptor(data_keys=frame_data_keys,
                                                                name=stream_name,
                                                                )
            yield 'descriptor', frame_stream_bundle.descriptor_doc

            # TODO: use event_page; wasn't working because of timestamps x "array" dtype issue
            for i in range(frames):
                data = np.random.random(DATA_SHAPE)
                yield 'event', frame_stream_bundle.compose_event(data={field: data for field in fields},
                                                                      timestamps={field: time.time() for field in fields})

        yield 'stop', run_bundle.compose_stop()
    return doc_gen(streams)


@fixture
def random_data_catalog(request: SubRequest) -> BlueskyInMemoryCatalog:
    N, frames = request.param
    catalog = BlueskyInMemoryCatalog()

    for i in range(N):
        docs = list(doc_stream(streams=["primary", "baseline"], fields=["cam1", "cam2"], frames=frames))
        start = docs[0][1]
        stop = docs[-1][1]

        def doc_gen():
            yield from docs

        catalog.upsert(start, stop, doc_gen, [], {})

    return catalog


# Test the catalog generation
@pytest.mark.parametrize("random_data_catalog", ((1, 1),), indirect=True)
def test_catalog(random_data_catalog):
    assert random_data_catalog[-1].primary.to_dask()['cam1'].compute() is not None


# Test the library widget with simple numpy arrays
def test_library_widget(qtbot):
    w = QWidget()
    w.setLayout(QHBoxLayout())

    l = LibraryWidget()
    for i in range(15):
        l.add_image(np.random.random((1000, 1000)), f"Sample {i+1}")

    s = QSlider()
    s.valueChanged.connect(partial(l.set_slice, axis="E"))

    w.layout().addWidget(l)
    w.layout().addWidget(s)

    w.show()

    qtbot.addWidget(w)
    # qtbot.stopForInteraction()


# Test the LibraryView bound to a catalog of runs
@pytest.mark.parametrize("random_data_catalog", ((10, FRAMES),), indirect=True)
def test_library_view(qtbot, random_data_catalog):
    from xicam.plugins.catalogplugin import CatalogModel
    model = CatalogModel(random_data_catalog)

    w = QWidget()
    w.setLayout(QHBoxLayout())

    l = LibraryView(model, slice={"E":0})

    s = QSlider()
    s.valueChanged.connect(partial(l.set_slice, axis="E"))

    w.layout().addWidget(l)
    w.layout().addWidget(s)

    w.show()

    qtbot.addWidget(w)
    # qtbot.stopForInteraction()
