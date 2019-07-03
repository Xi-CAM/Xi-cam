# -*- mode: python -*-
# Usage: pyinstall --path=C:\Windows\System32\downlevel Xi-cam.spec

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

block_cipher = None

from xicam.gui import static
datas_src = [path for path in glob.glob(os.path.join(static.__path__[0],'**/*.*'), recursive=True) if '__init__.py' not in path]
datas_dst = [os.path.dirname(os.path.relpath(path,static.__path__[0])) for path in datas_src]

datas_src.append(os.path.join(distributed.__path__[0],'distributed.yaml'))
datas_dst.append('distributed')

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

pluginmanager.collectPlugins(paths=[xicam.core.__path__[0],xicam.plugins.__path__[0],xicam.gui.__path__[0]])
plugins = pluginmanager.getAllPlugins()
datas_src.extend([plugin.path for plugin in plugins])
datas_dst.extend(['plugins']*len(plugins))

markerfiles = list(map(os.path.abspath, glob.glob('**/*.yapsy-plugin', recursive=True)))
datas_src.extend(markerfiles)
datas_dst.extend(['plugins']*len(markerfiles))


a = Analysis(['run_xicam.py'],
             pathex=['C:\\Users\\rp\\PycharmProjects\\Xi-cam'],
             binaries=[],
             datas=zip(datas_src, datas_dst),
             hiddenimports=['pandas._libs.tslibs.timedeltas',
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
                            ],
             hookspath=[],
             runtime_hooks=[],
             excludes=['astropy', 'qtmodern', 'pip', 'PyQt5'],  # included in data
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='Xi-cam',
          debug=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='Xi-cam')
