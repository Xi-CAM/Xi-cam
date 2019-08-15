from dask.diagnostics import Profiler, ResourceProfiler, CacheProfiler
from dask.diagnostics import visualize
import dask.threaded
from distributed import LocalCluster
from xicam.core import msg
from appdirs import user_config_dir
from .daskexecutor import DaskExecutor


class LocalExecutor(DaskExecutor):
    def execute(self, wf, client=None):
        if not client:
            client = dask.threaded
        return super(LocalExecutor, self).execute(wf, client)
