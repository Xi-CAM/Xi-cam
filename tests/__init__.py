def test_IFileFormatPlugin():
    import numpy as np
    import fabio
    from ..IFileFormatPlugin import IFileFormatPlugin

    class npyImage(IFileFormatPlugin):
        DEFAULT_EXTENTIONS = [".npy"]

        def read(self, fname, frame=None):
            np.load(fname)

        def write(self, fname):
            np.save(fname, self.data)

        _readheader = dict

    data = np.ones((101, 100))
    fname = 'test.npy'

    f = npyImage(data=data)
    f.write(fname)
    del f

    f = fabio.open(fname)
    assert np.all(np.equal(f.data, data))
    del f

    # cleanup
    import os
    os.remove(fname)


def test_IFittableModelPlugin():
    from ..IFittableModelPlugin import IFittable1DModelPlugin
    import numpy as np
    from astropy.modeling.fitting import LevMarLSQFitter
    from astropy.modeling import Parameter

    # Below example copied from AstroPy for demonstration; Gaussian1D is already a member of astropy's models
    class Gaussian1D(IFittable1DModelPlugin):
        amplitude = Parameter("amplitude")
        mean = Parameter("mean")
        stddev = Parameter("stddev")

        @staticmethod
        def evaluate(x, amplitude, mean, stddev):
            """
            Gaussian1D model function.
            """
            return amplitude * np.exp(- 0.5 * (x - mean) ** 2 / stddev ** 2)

        @staticmethod
        def fit_deriv(x, amplitude, mean, stddev):
            """
            Gaussian1D model function derivatives.
            """

            d_amplitude = np.exp(-0.5 / stddev ** 2 * (x - mean) ** 2)
            d_mean = amplitude * d_amplitude * (x - mean) / stddev ** 2
            d_stddev = amplitude * d_amplitude * (x - mean) ** 2 / stddev ** 3
            return [d_amplitude, d_mean, d_stddev]

    # Generate fake data
    np.random.seed(0)
    x = np.linspace(-5., 5., 200)
    m_ref = Gaussian1D(amplitude=2., mean=1, stddev=3)
    from astropy.modeling.models import Gaussian1D
    Gaussian1D()(x)
    y = m_ref(x) + np.random.normal(0., 0.1, x.shape)

    # Fit model to data
    m_init = Gaussian1D()

    fit = LevMarLSQFitter()
    m = fit(m_init, x, y)

    assert round(m.amplitude.value) == 2
    assert round(m.mean.value) == 1
    assert round(m.stddev.value) == 3


def test_IProcessingPlugin():
    from ..IProcessingPlugin import IProcessingPlugin, Input, Output

    class SumProcessingPlugin(IProcessingPlugin):
        a = Input(default=1, unit='nm', min=0)
        b = Input(default=2)
        c = Output()

        def evaluate(self):
            self.c.value = self.a.value + self.b.value
            return self.c.value

    t = SumProcessingPlugin()
    assert t.evaluate() == 3
    assert t.inputs['a'].name=='a'
    assert t.outputs['c'].name=='c'
    assert t.outputs['c'].value == 3


def makeapp():
    from qtpy.QtWidgets import QApplication
    app = QApplication([])
    return app


def mainloop():
    from qtpy.QtWidgets import QApplication
    app = QApplication.instance()
    app.exec_()


def test_IDataSourcePlugin():
    from ..IDataResourcePlugin import IDataResourcePlugin, IDataSourceListModel

    class SpotDataResourcePlugin(IDataResourcePlugin):
        def __init__(self, user='anonymous', password='',
                     query='skipnum=0&sortterm=fs.stage_date&sorttype=desc&search=end_station=bl832'):
            scheme = 'https'
            host = 'portal-auth.nersc.gov'
            path = 'als/hdf/search'
            config = {'scheme': scheme, 'host': host, 'path': path, 'query': query}
            super(SpotDataResourcePlugin, self).__init__(flags={'canPush': False}, **config)
            from requests import Session
            self.session = Session()
            self.session.post("https://newt.nersc.gov/newt/auth", {"username": user, "password": password})
            r = self.session.get(
                'https://portal-auth.nersc.gov/als/hdf/search?skipnum=0&limitnum=10&sortterm=fs.stage_date&sorttype=desc&search=end_station=bl832')
            self._data = eval(r.content.replace(b'false', b'False'))

        def columnCount(self, index=None):
            return len(self._data[0])

        def rowCount(self, index=None):
            return len(self._data)

        def data(self, index, role):
            from qtpy.QtCore import Qt, QVariant
            if index.isValid() and role == Qt.DisplayRole:
                return QVariant(self._data[index.row()]['name'])
            else:
                return QVariant()

                # TODO: remove qtcore dependence

    app = makeapp()
    from qtpy.QtWidgets import QListView

    # TODO: handle password for testing
    spot = IDataSourceListModel(SpotDataResourcePlugin())

    lv = QListView()
    lv.setModel(spot)
    lv.show()
    mainloop()