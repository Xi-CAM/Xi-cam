#!/usr/bin/env bash
source venv/bin/activate
cd core
rm -rf build/ dist/
python setup.py bdist_wheel sdist bdist_egg
twine upload --repository testpypi dist/*
cd ../plugins
rm -rf build/ dist/
python setup.py bdist_wheel sdist bdist_egg
twine upload --repository testpypi dist/*
cd ../gui
rm -rf build/ dist/
python setup.py bdist_wheel sdist bdist_egg
twine upload --repository testpypi dist/*
cd ../xicam
rm -rf build/ dist/
python setup.py bdist_wheel sdist bdist_egg
twine upload --repository testpypi dist/*