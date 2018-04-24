# flake8: noqa
from setuptools import Extension, find_packages, setup

from glob import iglob

from setup_utils import get_data_files, get_package_data, is_win, is_darwin
from version import __version__


packages = find_packages()
package_data = get_package_data(packages, exclude=('.py', '.pyc', '.cpp', '.h'))
opcode_src = list(iglob("vendor/opcode/**/*.cpp", recursive=True))

compile_args = []
runtime_library_dirs = []
libraries = []
if is_win:
    compile_args = ["/DICE_NO_DLL", "/DBAN_OPCODE_AUTOLINK"]
    libraries = ["boost_python36-vc141-mt-x64-1_67", "boost_numpy36-vc141-mt-x64-1_67"]
else:
    runtime_library_dirs = ["$ORIGIN"]
    libraries = ["boost_python36", "boost_numpy36"]

setup(
    name='pyopcode',
    version=__version__,
    packages=packages,
    install_requires=['numpy ~= 1.14'],
    ext_modules=[
        Extension('pyopcode.api', ['pyopcode/api.cpp'] + opcode_src,
                  include_dirs=['build_boost/include', 'build_boost/include/boost-1_67', 'vendor', 'vendor/opcode', 'vendor/opcode/Ice'],
                  library_dirs=['pyopcode'],
                  libraries=libraries,
                  runtime_library_dirs=runtime_library_dirs,
                  extra_compile_args=compile_args),
    ],
    package_data=package_data,
    include_package_data=True,
)
