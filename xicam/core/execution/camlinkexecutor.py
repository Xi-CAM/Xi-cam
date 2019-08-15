import json
from dask.diagnostics import Profiler, ResourceProfiler, CacheProfiler
from dask.diagnostics import visualize
import dask.threaded
from xicam.core import msg
from appdirs import user_config_dir

try:
    from camlink.services import graph as task_graph
except ImportError:
    print("CAMLINK is not installed; functionally coming soon™...")
import distributed
from .daskexecutor import DaskExecutor

client = None


class CamLinkExecutor(DaskExecutor):
    def execute(self, wf, client=None):
        # global client, graph

        services = {
            "machines": [
                {
                    "name": "freyja",
                    "address": "freyja.nsls2.bnl.gov",
                    "port": 22,
                    "username": "rp",
                    "password": "keyfile:/home/rp/.ssh/id_rsa",
                    "environment": {"PYTHONUSERBASE": "/tmp"},
                    "config_dir": "/tmp/camera",
                }
            ],
            "graph": {
                "configure": [{"machine": "freyja", "apps": [{"name": "dask/dask-scheduler"}], "tasks": ["dask-cluster"]}]
            },
        }

        services = json.dumps(services)
        print(services)

        graph = task_graph.Graph()
        graph.parse_stream(services)
        graph.start_tasks()
        graph.connect()
        graph.execute()

        meta_data = graph.machines[0].tasks[0].request_meta_data()

        local_port = graph.machines[0].node.get_free_local_port()
        remote_port = meta_data[0][0]
        print(local_port, remote_port)
        graph.machines[0].node.forward_tunnel(local_port, "localhost", remote_port)

        client = distributed.Client("tcp://localhost:" + str(local_port))

        return super(CamLinkExecutor, self).execute(wf, client)[0]
