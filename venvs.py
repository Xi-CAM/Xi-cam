import pathlib

import virtualenv
from appdirs import user_config_dir, site_config_dir

user_venv_dir = user_config_dir('xicam/venvs')
site_venv_dir = site_config_dir('xicam/venvs')

venvs = {}

execfile = lambda filename, globals=None, locals=None: exec(open(filename).read(), globals, locals)


def create_environment(name):
    virtualenv.create_environment(str(pathlib.Path(user_venv_dir, name)), site_packages=False, clear=False,
                                  unzip_setuptools=False,
                                  prompt=None, search_dirs=None, download=False,
                                  no_setuptools=False, no_pip=False, no_wheel=False,
                                  symlink=True)


def use_environment(name):
    activate_script = str(pathlib.Path(user_venv_dir, name, "bin", "activate_this.py"))
    execfile(activate_script, dict(__file__=activate_script))


use_environment("default")
# create_environment("default")

current_environment = str(pathlib.Path(user_venv_dir, "default"))
