from virtualenv.run import cli_run as virtualenv
from xicam.gui.cammart.venvs import activate_this
from pip._internal import main as pip
import subprocess

if __name__ == '__main__':

    # create clean build venv
    virtualenv(['build-venv', '--clear', '--copies'])

    # activate that venv
    activate_this('build-venv')

    # install xicam and its dependencies in the venv
    pip(['install', '.'])

    # Run NSIS to make an installer; check that its successful
    assert not subprocess.call(['makensis', 'installer.nsi'])
