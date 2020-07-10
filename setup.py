"""
Usage: pip install -e .
       python setup.py install
       python setup.py bdist_wheel
       python setup.py sdist bdist_egg
       twine upload dist/*
"""

# NOTE: Requires cx_freeze==6.0.b1 for linux builds

import sys
import versioneer
from codecs import open
from os import path

# These bits don't get collected automatically when packaging:
loosebits = ["numpy.core._methods", "numpy.lib.recfunctions"]

from setuptools import setup, find_packages, find_namespace_packages

# Set the long_description from the README
here = path.abspath(path.dirname(__file__))
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="xicam",
    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="The CAMERA platform for synchrotron data management, visualization, and reduction.",
    long_description=long_description,
    # The project's main homepage.
    url="https://github.com/Xi-cam/Xi-cam",
    download_url="https://pypi.org/project/xicam/",
    # Author details
    author="Ronald J Pandolfi",
    author_email="ronpandolfi@lbl.gov",
    # Choose your license
    license="BSD",
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        "Development Status :: 3 - Alpha",
        # Indicate who your project is intended for
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Physics",
        # Pick your license as you wish (should match "license" above)
        "License :: OSI Approved :: BSD License",
        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        "Programming Language :: Python :: 3.7",
    ],
    # What does your project relate to?
    keywords="synchrotron analysis x-ray scattering tomography ",
    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=find_packages() + find_namespace_packages(include=["xicam.*"]),
    package_dir={},
    # Alternatively, if you want to distribute just a my_module.py, uncomment
    # this:
    py_modules=["xicam._version", "xicam.run_xicam", "xicam.run_headless"],
    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=["PyQt5>=5.9.2",
                      "pathlib",
                      "qtpy",
                      "astropy",
                      "numpy>=1.16.0",
                      "appdirs",
                      "qdarkstyle",
                      "qtmodern",
                      "databroker>=1.0.0b8",
                      "distributed",
                      "dask",
                      "astropy",
                      "virtualenv",
                      "requests",
                      "appdirs",
                      "entrypoints",
                      "pyqtgraph==0.10.0",
                      "qtconsole", ],
    setup_requires=["cython"],  # cython is a missing required dep of astropy
    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,tests]
    extras_require={
        "docs": ["sphinx", "recommonmark", "sphinx_bootstrap_theme", "sphinx-markdown-tables"],
        "tests": ["pytest", "coverage", "coveralls", "codecov", "pylint", "pytest-qt", "pytest-cov"],
        "pyqt5": ["pyqt5"],
        "PySide2": ["PySide2"],
    },
    # If there are data files included in your packages that need to be
    # installed, specify them here.  If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    package_data={},
    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages. See:
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files # noqa
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    # data_files=[#('lib/python2.7/site-packages/gui', glob.glob('gui/*')),
    #            ('lib/python2.7/site-packages/yaml/tomography',glob.glob('yaml/tomography/*'))],
    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
        "gui_scripts": ["xicam=xicam.run_xicam:main"],
        "xicam.plugins.DataHandlerPlugin": ["npy = xicam.core.formats.NPYPlugin:NPYPlugin"],
        "xicam.plugins.PluginType": [
            "CatalogPlugin = xicam.plugins.catalogplugin:CatalogPlugin",
            "ControllerPlugin = xicam.plugins.controllerplugin:ControllerPlugin",
            "DataHandlerPlugin = xicam.plugins.datahandlerplugin:DataHandlerPlugin",
            "DataResourcePlugin = xicam.plugins.dataresourceplugin:DataResourcePlugin",
            "EZPlugin = xicam.plugins.ezplugin:_EZPlugin",
            "Fittable1DModelPlugin = xicam.plugins.fittablemodelplugin:Fittable1DModelPlugin",
            "GUIPlugin = xicam.plugins.guiplugin:GUIPlugin",
            'OperationPlugin = xicam.plugins.operationplugin:OperationPlugin',
            "SettingsPlugin = xicam.plugins.settingsplugin:SettingsPlugin",
            "QWidgetPlugin = xicam.plugins.widgetplugin:QWidgetPlugin",
        ],
        "xicam.plugins.SettingsPlugin": [
            "logging = xicam.gui.settings.logging:LoggingSettingsPlugin",
            "appearance = xicam.gui.settings.appearance:AppearanceSettingsPlugin",
            "execution = xicam.gui.settings.execution:ExecutionSettingsPlugin",
            "connections = xicam.gui.connections:ConnectionSettingsPlugin",
            "cammart = xicam.gui.cammart:CamMartSettingsPlugin",
            "venvs = xicam.gui.cammart.venvs:VenvsSettingsPlugin",
        ],
        "xicam.plugins.CatalogPlugin": [
            "databroker_catalog_plugin = xicam.gui.bluesky.databroker_catalog_plugin:DatabrokerCatalogPlugin"
        ],
    },
    ext_modules=[],
    include_package_data=True,
)
