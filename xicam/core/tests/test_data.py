def test_lazyfield():
    import fabio
    from xicam.core.data import lazyfield
    class Handler(object):
        def __init__(self, path):
            self.path = path

        def __call__(self, *args, **kwargs):
            return fabio.open(self.path).data

    l = lazyfield(Handler, '/home/rp/data/YL1031/YL1031__2m_00000.edf')
    assert l.asarray() is not None


    # def test_data():
    #     from .. import data
    #     data.load_header(filenames='/home/rp/data/YL1031/YL1031__2m_00000.edf')
