FROM quay.io/pypa/manylinux1_x86_64

WORKDIR /io

ENV PATH=/opt/python/cp36-cp36m/bin:$PATH
RUN pip install pipenv --upgrade

COPY Pipfile .
RUN pipenv install --dev --system --skip-lock

RUN wget -qO- https://dl.bintray.com/boostorg/release/1.67.0/source/boost_1_67_0.tar.gz | tar xz
COPY setup_utils.py .
COPY build_boost.py .
RUN python build_boost.py

COPY vendor/opcode ./vendor/opcode
COPY vendor/opcode/Ice ./vendor/opcode/Ice
COPY pyopcode/__init__.py ./pyopcode
COPY pyopcode/api.cpp ./pyopcode
COPY version.py .
COPY setup.py .
RUN python setup.py build_ext -if

COPY tests/ ./tests
COPY setup.cfg .
RUN flake8
RUN PYTHONPATH=. pytest
RUN python setup.py bdist_wheel
RUN auditwheel repair ./dist/pyopcode* -w ./dist/repaired
