# pyopcode

The one and only. To get started with development:

* Download a boost tarball and unpack into repo root, so you have a folder 'boost_1_67_0' in the root.
* Run `pipenv install --dev`.
* Run `pipenv run python build_boost.py`.
* Run `pipenv run python setup.py build_ext -if`, and repeat this call whenever you change something in `api.cpp`.

Housekeeping:

* Run `pipenv run flake8`
* Run `PYTHONPATH=. pipenv run pytest`

Distribution:

* Run `pipenv run python setup.py bdist_wheel`

# Windows Caveats

* `Pipfile.lock` was generated on Linux, so make sure to additionally pass `--skip-lock` to the `pipenv install` command.
* Pipenv doesn't copy over the `libs` folder from the root env to the virtualenv. Do this manually after running the `pipenv install` command.
* Make sure to have VS2017 build tools installed!

# manylinux1

To get the manylinux1 stamp of approval, build using the provided Dockerfile.

* Run `docker build . -t pyopcode`
* Run `docker run --rm pyopcode cat /io/dist/repaired/pyopcode-0.3.5-cp36-cp36m-manylinux1_x86_64.whl > dist/pyopcode-0.3.5-cp36-cp36m-manylinux1_x86_64.whl`
