#!/bin/bash

BUILD_CONFIG=Release

# use globs to take into account various possible suffixes: m, u, d
PYTHON_LIBRARY=`ls -d ${PREFIX}/lib/libpython* | head -n 1`
PYTHON_INCLUDE=`ls -d ${PREFIX}/include/python* | head -n 1`

cd pyopcode
mkdir build
cd build

# we are now (20171214) building with boost 1.65 and up.
# we prefer building with non-legacy libs, that is with libc++

# if [ `uname` = "Darwin" ]; then
#     # Specify same compiler as with which boost (1.61) is compiled
#     CXX_FLAGS="${CXX_FLAGS} -stdlib=libstdc++"
# fi

cmake ../src \
    -Wno-dev \
    -DCMAKE_BUILD_TYPE=${BUILD_CONFIG} \
    -DCMAKE_CXX_FLAGS="${CXX_FLAGS} -Wreturn-type" \
    ${MACOSX_DEPLOYMENT_TARGET:+-DCMAKE_OSX_DEPLOYMENT_TARGET='10.9'} \
    -DCMAKE_INSTALL_PREFIX=${PREFIX} \
    -DPYTHON_INCLUDE_DIR:PATH=${PYTHON_INCLUDE} \
    -DPYTHON_LIBRARY:FILEPATH=${PYTHON_LIBRARY} \
    -DNUMPY_INCLUDE_DIR:PATH="${SP_DIR}/numpy/core/include" \
    -DBOOST_INCLUDEDIR:PATH="${PREFIX}/include" \
    -DBOOST_LIBRARYDIR:PATH="${PREFIX}/lib"

make -j${CPU_COUNT}

cd ..

cp ./build/lib_pyopcode.so "${PREFIX}/lib/python${PY_VER}/_pyopcode.so"

cd ..

python setup.py bdist
python setup.py install
