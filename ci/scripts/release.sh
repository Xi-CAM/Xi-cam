#!/bin/bash

source $(dirname "${BASH_SOURCE[0]}")/setupenv.sh

cd $GITHUB_WORKSPACE
pip install --upgrade setuptools wheel twine
python setup.py bdist bdist_wheel bdist_egg

check=$(twine check dist/*)
if [ $check -gt 0 ]; then
    echo "Twine failed when checking dist/"
    exit 1
fi
exit 0
