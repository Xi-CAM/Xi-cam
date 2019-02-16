import pathlib

import sys, os
import venv
from appdirs import user_config_dir, site_config_dir, user_cache_dir
import subprocess
import platform
import os
import os.path
import pkgutil
import sys
import tempfile
import ensurepip

op_sys = platform.system()
if op_sys == 'Darwin':  # User config dir incompatible with venv on darwin (space in path name conflicts)
    user_venv_dir = os.path.join(user_cache_dir(appname='xicam'),'venvs')
else:
    user_venv_dir = os.path.join(user_config_dir(appname='xicam'),'venvs')
site_venv_dir = os.path.join(site_config_dir(appname='xicam'),'venvs')

venvs = {}
observers = []

# Python 2 style execfile function
execfile = lambda filename, globals=None, locals=None: exec(open(filename).read(), globals, locals)

# TODO: transition to http://virtualenvwrapper.readthedocs.io/en/latest/index.html

class EnvBuilder(venv.EnvBuilder):
    def _setup_pip(self, context):
        """ Override normal behavior using subprocess, call ensurepip directly"""
        self.bootstrap(root=os.path.dirname(os.path.dirname(context.env_exe)), upgrade=True, default_pip=True)

    @staticmethod
    def bootstrap(*, root=None, upgrade=False, user=False,
                  altinstall=False, default_pip=False,
                  verbosity=0):
        """
        Bootstrap modified from ensurepip to avoid issues with parent environment
        """
        if altinstall and default_pip:
            raise ValueError("Cannot use altinstall and default_pip together")

        ensurepip._disable_pip_configuration_settings()

        # By default, installing pip and setuptools installs all of the
        # following scripts (X.Y == running Python version):
        #
        #   pip, pipX, pipX.Y, easy_install, easy_install-X.Y
        #
        # pip 1.5+ allows ensurepip to request that some of those be left out
        if altinstall:
            # omit pip, pipX and easy_install
            os.environ["ENSUREPIP_OPTIONS"] = "altinstall"
        elif not default_pip:
            # omit pip and easy_install
            os.environ["ENSUREPIP_OPTIONS"] = "install"

        with tempfile.TemporaryDirectory() as tmpdir:
            # Put our bundled wheels into a temporary directory and construct the
            # additional paths that need added to sys.path
            additional_paths = []
            for project, version in ensurepip._PROJECTS:
                wheel_name = "{}-{}-py2.py3-none-any.whl".format(project, version)
                whl = pkgutil.get_data(
                    "ensurepip",
                    "_bundled/{}".format(wheel_name),
                )
                with open(os.path.join(tmpdir, wheel_name), "wb") as fp:
                    fp.write(whl)

                additional_paths.append(os.path.join(tmpdir, wheel_name))

            # Construct the arguments to be passed to the pip command
            args = ["install", "--no-index", "--find-links", tmpdir]
            if root:
                args += ["--prefix", root] ######## Modified
            if upgrade:
                args += ["--upgrade"]
            if user:
                args += ["--user"]
            if verbosity:
                args += ["-" + "v" * verbosity]

            args += ['--ignore-installed'] ######## Added

            print('boostrap:', *(args + [p[0] for p in ensurepip._PROJECTS]))
            EnvBuilder._run_pip(args + [p[0] for p in ensurepip._PROJECTS], additional_paths)

    @staticmethod
    def _run_pip(args, additional_paths=None):
        oldpath=sys.path

        # Add our bundled software to the sys.path so we can import it
        if additional_paths is not None:
            sys.path = additional_paths + sys.path

        # Install the bundled software
        import pip
        pip.main(args)

        # Restore sys.path
        sys.path=oldpath


def create_environment(name: str):
    """
    Create a new sandbox environment in the user_venv_dir with name name.

    Parameters
    ----------
    name : str
        Name of sandbox environment to create.
    """

    envpath = pathlib.Path(user_venv_dir, name)
    if envpath.is_dir():
        return
        # raise ValueError('Environment already exists.')
    EnvBuilder(with_pip=True).create(envpath)


def use_environment(name):
    """
    Activate the sandbox environment with name name in user_venv_dir

    Parameters
    ----------
    name : str
        Name of sandbox environment to activate
    """
    path = pathlib.Path(user_venv_dir, name)
    if not path.is_dir():
        raise ValueError(f"Sandbox environment '{name}' could not be found.")

    global current_environment
    current_environment = str(path)
    activate_this(current_environment)

    for observer in observers:
        observer.venvChanged()


def activate_this(path):
    # Below copied and modified from the activate_this.py module of virtualenv, which is missing form venv
    old_os_path = os.environ.get('PATH', '')
    os.environ['PATH'] = os.path.dirname(os.path.abspath(path)) + os.pathsep + old_os_path
    base = os.path.dirname(os.path.dirname(os.path.abspath(path)))
    if sys.platform == 'win32':
        site_packages = os.path.join(base, 'Lib', 'site-packages')
    else:
        site_packages = os.path.join(base, 'lib', 'python%s' % sys.version[:3], 'site-packages')
    prev_sys_path = list(sys.path)
    # if not getattr(sys, 'frozen', False):  # site missing addsitedir when frozen
    import site
    site.addsitedir(site_packages)

    sys.real_prefix = sys.prefix
    sys.prefix = base
    # Move the added items to the front of the path:
    new_sys_path = []
    for item in list(sys.path):
        if item not in prev_sys_path:
            new_sys_path.append(item)
            sys.path.remove(item)
    sys.path[:0] = new_sys_path


current_environment = ''

# TODO: find all venvs; populate the venvs global
def initialize_venv():
    global current_environment
    create_environment("default")
    use_environment("default")
    current_environment = str(pathlib.Path(user_venv_dir, "default"))
