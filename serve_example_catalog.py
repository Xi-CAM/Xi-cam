import subprocess
import time
from suitcase.mongo_normalized import Serializer
from bluesky import RunEngine
from ophyd.sim import det, motor
from mongobox import MongoBox
from bluesky.plans import scan, count


box = MongoBox()
box.start()
client = box.client()
serializer = Serializer(client['mds'], client['assets'])

RE = RunEngine()
RE.subscribe(serializer)
RE(count([det]))
RE(count([det], 5))
RE(scan([det], motor, -1, 1, 7))

def extract_uri(db):
    return f'mongodb://{db.client.address[0]}:{db.client.address[1]}/{db.name}'

with open('/tmp/test_catalog_for_bluesky_browser.yml', 'w') as f:
    f.write(f'''
plugins:
  source:
    - module: intake_bluesky
sources:
  xyz:
    description: Some imaginary beamline
    driver: intake_bluesky.mongo_normalized.BlueskyMongoCatalog
    container: catalog
    args:
        metadatastore_db: {extract_uri(client['mds'])}
        asset_registry_db: {extract_uri(client['assets'])}
        handler_registry:
          NPY_SEQ: ophyd.sim.NumpySeqHandler
    metadata:
        beamline: "00-ID"
    ''')

process = subprocess.Popen(['intake-server', '/tmp/test_catalog_for_bluesky_browser.yml'])
process.wait()
