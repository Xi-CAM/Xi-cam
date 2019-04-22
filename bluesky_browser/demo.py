from pathlib import Path
import subprocess
import tempfile
import time

from suitcase.jsonl import Serializer
from bluesky import RunEngine
from ophyd.sim import det, motor
from bluesky.plans import scan, count
from event_model import RunRouter
import intake_bluesky.jsonl  # noqa; to force intake registration


def generate_example_data(data_path):
    data_path = Path(data_path)

    def factory(name, doc):
        serializer = Serializer(data_path / 'abc')
        serializer('start', doc)
        return [serializer], []

    RE = RunEngine()
    rr = RunRouter([factory])
    RE.subscribe(rr)
    RE(count([det]))
    RE(count([det], 5))
    RE(scan([det], motor, -1, 1, 7))

    def factory(name, doc):
        serializer = Serializer(data_path / 'xyz')
        serializer('start', doc)
        return [serializer], []

    RE = RunEngine()
    rr = RunRouter([factory])
    RE.subscribe(rr)
    RE(count([det], 3))

    catalog_filepath = data_path / 'catalog.yml'
    with open(catalog_filepath, 'w') as file:
        file.write(f'''
plugins:
  source:
    - module: intake_bluesky
sources:
  abc:
    description: Some imaginary beamline
    driver: intake_bluesky.jsonl.BlueskyJSONLCatalog
    container: catalog
    args:
      paths: {Path(data_path) / 'abc' / '*.jsonl'}
      handler_registry:
        NPY_SEQ: ophyd.sim.NumpySeqHandler
    metadata:
      beamline: "00-ID"
  xyz:
    description: Some imaginary beamline
    driver: intake_bluesky.jsonl.BlueskyJSONLCatalog
    container: catalog
    args:
      paths: {Path(data_path) / 'xyz' / '*.jsonl'}
      handler_registry:
        NPY_SEQ: ophyd.sim.NumpySeqHandler
    metadata:
      beamline: "99-ID"
''')
    return str(catalog_filepath)
