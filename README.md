# pyopcode

Build locally:

* `python -m pip wheel -w wheelhouse --no-deps .`

Develop and test locally (replace `bin` with `Scripts` on windows):

* `python -m venv .venv`
* `.venv/bin/pip install -e .[dev]`
* `.venv/bin/pytest tests`
* `.venv/bin/black .`

Release by pushing a tag that starts with `v`. E.g. `v0.4.0`.
