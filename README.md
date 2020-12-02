[![PyPI](https://badge.fury.io/py/pyopcode.svg)](https://badge.fury.io/py/pyopcode) [![Anaconda](https://anaconda.org/conda-forge/pyopcode/badges/version.svg)](https://anaconda.org/conda-forge/pyopcode/) [![Travis](https://travis-ci.org/ClinicalGraphics/pyopcode.svg?branch=master)](https://travis-ci.org/ClinicalGraphics/pyopcode/)

# pyopcode

The one and only. To get started with development:

* Run `conda env create`
* Run `python -m pip install . -vvv && pytest -s`, and repeat this call whenever you change something in `api.cpp`.

Distribution:

* Run `conda build conda-recipe`. Building wheels is also supported.

# manylinux1

To get the manylinux1 stamp of approval, build using the provided Dockerfile.

* Run `docker build . -t pyopcode`
* Run `docker run --rm pyopcode cat /io/dist/repaired/pyopcode-0.3.5-cp36-cp36m-manylinux1_x86_64.whl > dist/pyopcode-0.3.5-cp36-cp36m-manylinux1_x86_64.whl`
