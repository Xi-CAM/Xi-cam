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

    def factory(name, doc):
        serializer = Serializer(str(data_path))
        serializer('start', doc)
        return [serializer], []

    RE = RunEngine()
    rr = RunRouter([factory])
    RE.subscribe(rr)
    RE(count([det]))
    RE(count([det], 5))
    RE(scan([det], motor, -1, 1, 7))
    
    catalog_filepath = Path(data_path) / 'catalog.yml'
    with open(catalog_filepath, 'w') as file:
        file.write(f'''
plugins:
  source:
    - module: intake_bluesky
sources:
  xyz:
    description: Some imaginary beamline
    driver: intake_bluesky.jsonl.BlueskyJSONLCatalog
    container: catalog
    args:
      paths: {Path(data_path) / '*.jsonl'}
      handler_registry:
        NPY_SEQ: ophyd.sim.NumpySeqHandler
    metadata:
      beamline: "00-ID"
''')
    with open(catalog_filepath) as file:
        file.read()
    return str(catalog_filepath)
