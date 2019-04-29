from pathlib import Path

from suitcase.jsonl import Serializer
from bluesky import RunEngine
from ophyd.sim import det, det4, noisy_det, motor, motor1, motor2, img
from bluesky.plans import scan, count, grid_scan
from bluesky.preprocessors import SupplementalData
from event_model import RunRouter
import intake_bluesky.jsonl  # noqa; to force intake registration


det.kind = 'hinted'
noisy_det.kind = 'hinted'
det4.kind = 'hinted'


def generate_example_data(data_path):
    data_path = Path(data_path)

    def factory(name, doc):
        serializer = Serializer(data_path / 'abc')
        serializer('start', doc)
        return [serializer], []

    RE = RunEngine()
    sd = SupplementalData()
    RE.preprocessors.append(sd)
    sd.baseline.extend([motor1, motor2])
    rr = RunRouter([factory])
    RE.subscribe(rr)
    RE(count([det]))
    RE(count([noisy_det], 5))
    RE(scan([det], motor, -1, 1, 7))
    RE(grid_scan([det4], motor1, -1, 1, 4, motor2, -1, 1, 7, False))
    RE(scan([det], motor, -1, 1, motor2, -1, 1, 5))
    RE(count([noisy_det, det], 5))
    # RE(count([img], 5))

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
