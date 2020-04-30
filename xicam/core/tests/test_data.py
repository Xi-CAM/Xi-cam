def test_lazyfield():
    import fabio
    from xicam.core.data import lazyfield

    class Handler(object):
        def __init__(self, path):
            self.path = path

        def __call__(self, *args, **kwargs):
            return fabio.open(self.path).data

    # l = lazyfield(Handler, '/home/rp/data/YL1031/YL1031__2m_00000.edf')
    # assert l.asarray() is not None

    # def test_data():
    #     from .. import data
    #     data.load_header(filenames='/home/rp/data/YL1031/YL1031__2m_00000.edf')


import os
import entrypoints
import numpy as np
from databroker.in_memory import BlueskyInMemoryCatalog


def test_ingestor(tmp_path):
    # test data
    data = np.random.random((1000, 1000))
    # write data to test edf
    edf_path = os.path.join(tmp_path, "test.edf")
    print("edf_path:", edf_path)
    EdfImage(data).write(edf_path)

    # get edf ingestor
    edf_ingestor = entrypoints.get_single("databroker.ingestors", "application/edf").load()

    # load data into catalog
    document = list(edf_ingestor([edf_path]))
    uid = document[0][1]["uid"]
    catalog = BlueskyInMemoryCatalog()
    # TODO -- change upsert signature to put start and stop as kwargs
    # TODO -- ask about more convenient way to get a BlueskyRun from a document generator
    catalog.upsert(document[0][1], document[-1][1], edf_ingestor, ([edf_path],), {})
    return catalog[uid]


if __name__ == "__main__":
    run = test_ingestor("/tmp")
    print(run)
    print(list(run.canonical(fill="yes")))
    print(run.primary.to_dask().values)
