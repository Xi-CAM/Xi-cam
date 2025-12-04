import dask.threaded

from .daskexecutor import DaskExecutor


class LocalExecutor(DaskExecutor):
    def execute(self, wf, client=None):
        if not client:
            client = dask.threaded
        return super(LocalExecutor, self).execute(wf, client)
