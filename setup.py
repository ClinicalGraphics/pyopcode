from setuptools import find_packages
from distutils.core import setup
import os
import sys

import pkg_conf

is_win = sys.platform.startswith("win")
shared_lib_path = os.path.join(sys.prefix, r"DLLs" if is_win else r"lib")
shared_lib_files = r'pyopcode/_pyopcode.pyd' if is_win else r'pyopcode/_pyopcode.so'
data_files = [(shared_lib_path, [shared_lib_files])]


setup(
    keywords = "OPCODE numpy",
    name=pkg_conf.PKG_NAME,
    version=pkg_conf.get_version(),
    packages=find_packages(),
    install_requires=['pyyaml'],
    description=pkg_conf.get_recipe_meta()['about']['summary'],
    long_description=pkg_conf.get_readme_rst(),
    author=pkg_conf.AUTHOR,
    author_email=pkg_conf.AUTHOR_EMAIL,
    url=pkg_conf.get_recipe_meta()['about']['home'],
    license=pkg_conf.get_recipe_meta()['about']['license'],
    platforms='any',
    data_files=data_files,
    classifiers=[
        "Development Status :: 4 - Beta",
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        "Topic :: Utilities",
        'Topic :: Scientific/Engineering',
        'License :: {}'.format(pkg_conf.get_recipe_meta()['about']['license']),
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
    ],
)
