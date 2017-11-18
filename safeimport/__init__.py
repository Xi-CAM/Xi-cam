#!/usr/bin/env python
# encoding: utf-8

# Based on https://gist.github.com/d0c-s4vage/14a34f3ad815906097ad
# Credit: d0c-s4vage

from imp import find_module

import pip
from pip.commands.search import SearchCommand

from .. import venvs
from ...core import msg


class PyPiPathHook(object):
    def __init__(self):
        pass
        # # create a virtualenv at ~/.pypi_autoload
        # user_home = os.path.expanduser("~")
        # self.venv_home = os.path.join(user_home, ".pypi_autoload")
        # if not os.path.exists(self.venv_home):
        #     virtualenv.create_environment(self.venv_home)
        # activate_script = os.path.join(self.venv_home, "bin", "activate_this.py")
        # execfile(activate_script, dict(__file__=activate_script))

    def find_module(self, fullname, path=None):
        if "." in fullname:
            return None

        try:
            mod = find_module(fullname)
        except ImportError as e:
            pass
        else:
            # it's already accessible, we don't need to do anything
            return None

        msg.showMessage(f'The "{fullname}" library is not installed.')
        msg.showMessage(f'Attempting automated install of "{fullname}".')

        if self._package_exists_in_pypi(fullname):
            pip.main(["install", fullname, "--prefix", venvs.current_environment])

        # we've made it accessible to the normal import procedures
        # now, (should be on sys.path), so we'll return None which
        # will make Python attempt a normal import
        return None

    def _package_exists_in_pypi(self, fullname):
        searcher = SearchCommand()
        options, args = searcher.parse_args([fullname])
        matches = searcher.search(args, options)
        found_match = None
        for match in matches:
            if match["name"].lower() == fullname:
                return True
                break

        return False

# sys.meta_path.append(PyPiPathHook())
