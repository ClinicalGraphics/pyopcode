from setuptools import setup

from glob import iglob
import sys

from pybind11.setup_helpers import Pybind11Extension, build_ext


is_win = sys.platform == "win32"

__version__ = "0.4.0"

# The main interface is through Pybind11Extension.
# * You can add cxx_std=11/14/17, and then build_ext can be removed.
# * You can set include_pybind11=false to add the include directory yourself,
#   say from a submodule.
#
# Note:
#   Sort input source files if you glob sources to ensure bit-for-bit
#   reproducible builds (https://github.com/pybind/python_example/pull/53)

opcode_src = sorted(iglob("vendor/opcode/**/*.cpp", recursive=True))
opcode_include = ["vendor", "vendor/opcode", "vendor/opcode/Ice"]

compile_args = []
if is_win:
    compile_args.extend(["/DICE_NO_DLL", "/DBAN_OPCODE_AUTOLINK"])

ext_modules = [
    Pybind11Extension(
        "pyopcode",
        ["src/api.cpp"] + opcode_src,
        include_dirs=opcode_include,
        extra_compile_args=compile_args,
    ),
]

setup(
    name="pyopcode",
    version=__version__,
    author="Korijn van Golen",
    author_email="korijn.vangolen@zimmerbiomet.com",
    url="https://github.com/ClinicalGraphics/pyopcode/",
    description="OPCODE python bindings",
    ext_modules=ext_modules,
    python_requires=">=3.6.0",
    install_requires=[
        "numpy>=1.15.0",
    ],
    extras_require={
        "dev": [
            "pytest",
            "black",
        ],
    },
    # Currently, build_ext only provides an optional "highest supported C++
    # level" feature, but in the future it may provide more features.
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
)
