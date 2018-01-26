from xicam.plugins import EZPlugin
from xicam.gui.static import path


def runtest():
    import numpy as np

    img = np.random.random((100, 100, 100))
    EZTest.setImage(img)

    hist = np.histogram(img, 100)
    EZTest.plot(hist[1][:-1], hist[0])


def opentest(filepaths):
    import fabio
    for filepath in filepaths:
        img = fabio.open(filepath).data
        EZTest.setImage(img)


EZTest = EZPlugin(name='EZTest',
                  toolbuttons=[(str(path('icons/calibrate.png')), runtest)],
                  parameters=[{'name': 'Test', 'value': 10, 'type': 'int'},
                              {'name': 'Fooo', 'value': True, 'type': 'bool'}],
                  openfileshandler=opentest)
