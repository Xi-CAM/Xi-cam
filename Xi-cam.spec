# -*- mode: python -*-
# TODO: ALERT! Before building, you MUST manually set the PYTHONPATH env-var as follows!
# WIN Preparation: set PYTHONPATH="C:\Users\rp\.virtualenvs\xi-cam2\Lib\site-packages"
# WIN Usage: pyinstaller --clean --onefile --noconsole --paths C:\Windows\System32\downlevel Xi-cam\Xi-cam.spec
# OSX Usage: pyinstaller --clean --onefile --noconsole --osx-bundle-identifier gov.lbl.camera.xicam Xi-cam.spec

import glob, os
import distributed
import astropy
import qtpy  # preload qtpy and QApplication so that manager thinks qt is safe
from qtpy import QtWidgets
qapp = QtWidgets.QApplication([])
from xicam.plugins import manager as pluginmanager
import xicam.plugins, xicam.core, xicam.gui
import qtmodern
import pip
import PyQt5
import dask
import xicam

block_cipher = None

from xicam.gui import static

# Some packages have messy non-py contents; Lets wrangle them!

# Xi-cam's static files
datas_src = [path for path in glob.glob(os.path.join(static.__path__[0],'**/*.*'), recursive=True) if '__init__.py' not in path] # TODO: filter this
datas_dst = [os.path.dirname(os.path.relpath(path,os.path.dirname(os.path.dirname(os.path.dirname(static.__path__[0])))))
             for path in datas_src]

# Astropy is a mess of file-based imports; must include source outside of pkg
datas_src.append(astropy.__path__[0])
datas_dst.append('astropy')

# qtmodern has lots of data files; including source
datas_src.append(qtmodern.__path__[0])
datas_dst.append('qtmodern')

# pip needs its certs
datas_src.append(pip.__path__[0])
datas_dst.append('pip')

# PyQt5 needs its binaries
datas_src.append(PyQt5.__path__[0])
datas_dst.append('PyQt5')

# Dask needs its config yaml
datas_src.append(dask.__path__[0])
datas_dst.append('dask')

# Distributed needs its yaml
datas_src.append(os.path.join(distributed.__path__[0],'distributed.yaml'))
datas_dst.append('distributed')

# Xi-cam has path sensitive marker-files
for path in list(xicam.__path__):
    xicam_src = glob.glob(os.path.join(path, '**/*.*'), recursive=True)
    xicam_src = list(filter(lambda path: os.path.splitext(path)[-1] in ['.py', '.yapsy-plugin'], xicam_src))
    datas_src.extend(xicam_src)
    datas_dst.extend([os.path.dirname(os.path.relpath(p,os.path.dirname(path))) for p in xicam_src])

print('datas:')
print(*list(zip(datas_src, datas_dst)),sep='\n')


a = Analysis(['run_xicam.py'],
             pathex=[os.getcwd(),
                     'C:\\Windows\\System32\\downlevel',],
             binaries=[],
             datas=zip(datas_src, datas_dst),
             hiddenimports=['pandas._libs.tslibs.timedeltas',
                            'imagecodecs._imagecodecs_lite',
                            'pandas._libs.tslibs.np_datetime',
                            'pandas._libs.tslibs.nattype',
                            'pandas._libs.tslibs',
                            'pandas._libs.skiplist',
                            'numpy.lib',
                            'numpy.lib.recfunctions',
                            'shelve',
                            'requests',
                            'qdarkstyle',
                            'xicam.core.execution',
                            'xicam.plugins.cammart',
                            'xicam.gui.widgets.dynimageview',
                            'compileall',
                            'xicam.gui.windows',
                            'xicam.core',
                            'xicam.plugins',
                            'xicam.gui'
                            ],
             hookspath=[],
             runtime_hooks=[],
             excludes=['astropy', 'qtmodern', 'pip', 'PyQt5'],  # included in data
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

# For onefile
# exe = EXE(pyz,
#           a.scripts,
#           a.binaries,
#           a.zipfiles,
#           a.datas,
#           name='Xi-cam',
#           debug=False,
#           strip=False,
#           upx=True,)

# For non-onefile
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='Xi-cam',
          debug=False,
          strip=False,
          upx=True,
          console=True,
          icon='xi-cam.gui\\xicam\\gui\\static\\icons\\xicam.ico')

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='Xi-cam')
