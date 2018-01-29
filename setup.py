"""
Usage: pip install -e .
       python setup.py install
       python setup.py bdist_wheel
       python setup.py sdist bdist_egg
       twine upload dist/*
"""

# NOTE: Requires cx_freeze==6.0.b1 for linux builds

import sys

deps = ['databroker', 'pathlib', 'qtpy', 'PyQt5', 'yapsy', 'astropy', 'signalslot', 'numpy', 'pyqtgraph', 'appdirs',
        'xicam.core', 'xicam.plugins', 'xicam.gui']

# These bits don't get collected automatically when packaging:
loosebits = ['numpy.core._methods', "numpy.lib.recfunctions"]

if sys.argv[1] in ['build', 'bdist_rpm', 'build_exe']:
    from cx_Freeze import setup, Executable
    import opcode, typing
    import os

    include_files = []
    excludes = []


    def include_package(packagename):
        pkg = __import__(packagename)
        path = [getattr(pkg, '__file__', None)]
        if not path[0]: path = getattr(pkg,'__path__', None)._path
        for p in path:
            if os.path.basename(p) == '__init__.py':
                p = os.path.dirname(p)
            include_files.append(p)
        if packagename in deps: deps.remove(packagename)
        excludes.append(packagename)
        print(f'Including path: {path}')


    def include_builtin(name):
        # opcode and typing are not virtualenv modules, so we can use them to find the stdlib; this is the same
        # trick used by distutils itself it installs itself into the virtualenv; one is for /usr/lib,
        # the other is /usr/lib64
        path = os.path.join(os.path.dirname(typing.__file__), name)
        if os.path.exists(path):
            include_files.append((path, name))
            print(f'Including path: {path}')
            return
        path = os.path.join(os.path.dirname(opcode.__file__), name)
        if os.path.exists(path):
            include_files.append((path, name))
            print(f'Including path: {path}')
            return




    # Some packages are messy under cx_freeze; this bypasses the import parsing and copies all contents directly
    include_package('astropy')
    include_package('virtualenv')
    include_package('_sysconfigdata_m_linux_x86_64-linux-gnu')
    include_package('xicam')
    include_package('site')
    include_package('yapsy')
    include_builtin('distutils/')
    include_builtin('typing.py')
    include_builtin('_sitebuiltins.py')

    # include the virtualenv's orig-prefix.txt
    # import pathlib, astropy
    # include_files.append(pathlib.Path(astropy.__file__).parent.parent.parent / 'orig-prefix.txt')

    # Dependencies are automatically detected, but it might need
    # fine tuning.
    buildOptions = dict(includes=deps + loosebits,
                        # namespace_packages=['xicam'],
                        excludes=["distutils"] + excludes,
                        include_files=include_files,
                        optimize=0)


    import sys

    base = 'Win32GUI' if sys.platform == 'win32' else None

    executables = [
        Executable('run_xicam.py', base=base, targetName='Xi-cam')
    ]

    setup(name='Xi-cam',
          version='2.1.1',
          description='The CAMERA platform for '
                      'synchrotron data management, visualization, and reduction.',
          options=dict(build_exe=buildOptions),
          executables=executables)

else:
    from setuptools import setup, find_packages

    setup(
        name='xicam',

        # Versions should comply with PEP440.  For a discussion on single-sourcing
        # the version across setup.py and the project code, see
        # https://packaging.python.org/en/latest/single_source_version.html
        version='2.1.1',

        description='The CAMERA platform for synchrotron data management, visualization, and reduction. This is a '
                    'namespace package containing xicam.core, xicam.plugins, and xicam.gui. ',

        # The project's main homepage.
        url='https://github.com/ronpandolfi/Xi-cam',

        # Author details
        author='Ronald J Pandolfi',
        author_email='ronpandolfi@lbl.gov',

        # Choose your license
        license='BSD',

        # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
        classifiers=[
            # How mature is this project? Common values are
            #   3 - Alpha
            #   4 - Beta
            #   5 - Production/Stable
            'Development Status :: 3 - Alpha',

            # Indicate who your project is intended for
            'Intended Audience :: Science/Research',
            'Topic :: Scientific/Engineering :: Physics',

            # Pick your license as you wish (should match "license" above)
            'License :: OSI Approved :: BSD License',

            # Specify the Python versions you support here. In particular, ensure
            # that you indicate whether you support Python 2, Python 3 or both.
            'Programming Language :: Python :: 3.6'
        ],

        # What does your project relate to?
        keywords='synchrotron analysis x-ray scattering tomography ',

        # You can just specify the packages manually here if your project is
        # simple. Or you can use find_packages().
        packages=find_packages(),

        package_dir={},

        # Alternatively, if you want to distribute just a my_module.py, uncomment
        # this:
        py_modules=["run_xicam"],

        # List run-time dependencies here.  These will be installed by pip when
        # your project is installed. For an analysis of "install_requires" vs pip's
        # requirements files see:
        # https://packaging.python.org/en/latest/requirements.html
        install_requires=deps,

        setup_requires=[],

        # List additional groups of dependencies here (e.g. development
        # dependencies). You can install these using the following syntax,
        # for example:
        # $ pip install -e .[dev,tests]
        extras_require={
            # 'dev': ['check-manifest'],
            'tests': ['pytest', 'coverage'],
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
        entry_points={'gui_scripts': ['xicam=run_xicam:main']},

        ext_modules=[],
        include_package_data=True
    )
