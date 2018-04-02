from dask.diagnostics import Profiler, ResourceProfiler, CacheProfiler
from dask.diagnostics import visualize
import dask.threaded
from xicam.core import msg
from appdirs import user_config_dir


class DaskExecutor(object):
    def execute(self, wf, client):
        if not wf.processes:
            return {}

        dsk = wf.convertGraph()

        with Profiler() as prof, ResourceProfiler(dt=0.25) as rprof, CacheProfiler() as cprof:
            result = client.get(dsk[0], dsk[1])

        msg.logMessage('result:', result, level=msg.DEBUG)
        path = user_config_dir('xicam/profile.html')
        visualize([prof, rprof, cprof], show=False, file_path=path)
        msg.logMessage(f'Profile saved: {path}')

        wf.lastresult = result

        return result
