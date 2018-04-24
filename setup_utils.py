from itertools import chain
from collections import defaultdict
from os.path import isfile, relpath, dirname, splitext, join, exists, expandvars
from setuptools.dist import Distribution
from glob import iglob
import inspect
import sys
from sysconfig import get_paths


is_win = (sys.platform == 'win32')
is_darwin = (sys.platform == 'darwin')


class BinaryDistribution(Distribution):
    """
    Specialized setuptools `Distribution` class that forces a platform-specific package build.

    In the scenario that you are not providing any Extensions to the ext_modules keyword argument of `setup()`, but
    would still like to build a platform-specific wheel, you can provide this class to the `distclass` keyword
    argument of `setup()`. Setuptools will then recognize your distribution as containing Extensions and build a
    platform-specific wheel.

    Examples
    --------
    >>> setup(distclass=BinaryDistribution)
    """

    def has_ext_modules(self):
        return True

    def __getattribute__(self, name):
        if name == "ext_modules":
            is_finalize_options_call = [frame for frame in inspect.stack()
                                        if frame.filename.endswith('install.py') and
                                        frame.function == 'finalize_options']
            if is_finalize_options_call:
                # this distutils function checks the self.ext_modules attribute directly for truthiness, instead
                # of calling self.has_ext_modules()
                return [True]  # any truthy list will do

        return super().__getattribute__(name)


def get_package_dir(package, package_dir=None):
    """
    Return the directory, relative to the top of the source distribution, where package 'package' should be found
    (at least according to the 'package_dir' option, if any).

    Notes
    -----
    Copied and modified source from distutils.command.build_py
    """
    if package_dir is None:
        package_dir = {}

    path = package.split('.')

    if not package_dir:
        if path:
            return join(*path)
        else:
            return ''
    else:
        tail = []
        while path:
            try:
                pdir = package_dir['.'.join(path)]
            except KeyError:
                tail.insert(0, path[-1])
                del path[-1]
            else:
                tail.insert(0, pdir)
                return join(*tail)
        else:
            # Oops, got all the way through 'path' without finding a
            # match in package_dir.  If package_dir defines a directory
            # for the root (nameless) package, then fallback on it;
            # otherwise, we might as well have not consulted
            # package_dir at all, as we just use the directory implied
            # by 'tail' (which should be the same as the original value
            # of 'path' at this point).
            pdir = package_dir.get('')
            if pdir is not None:
                tail.insert(0, pdir)

            if tail:
                return join(*tail)
            else:
                return ''


def get_package_data(packages, exclude=('.py', '.pyc'), package_dir=None):
    """
    Parameters
    ----------
    packages : iterable of str
        List of packages to collect files for
    exclude : iterable of str
        List of file extensions to exclude
    package_dir : mapping of str -> str
        Same as `package_dir` argument to `setup()`

    Returns
    -------
    mapping of str -> list of str
        `package_data` argument to `setup()`
    """
    dir_filter = lambda path: isfile(path)
    exclude_set = set(exclude)  # convert to set for more efficient lookup time
    exclude_filter = lambda path: splitext(path)[-1] not in exclude_set

    package_data = defaultdict(list)
    for package in packages:
        package_path = get_package_dir(package, package_dir=package_dir)
        for filename in filter(exclude_filter, filter(dir_filter, iglob(f"{package_path}/*"))):
            rel_filename = relpath(filename, package_path)
            package_data[package].append(rel_filename)

    return package_data


def get_data_files(prefix, paths):
    """
    Parameters
    ----------
    prefix : str
        All other parameters and returned values are relative to this path prefix
    paths : list of str
        Paths relative to `prefix` containing data files

    Returns
    -------
    sequence of (directory, files) pairs.
        `data_files` argument to `setup()`
    """
    dir_filter = lambda path: isfile(path)
    files = chain.from_iterable([filter(dir_filter, iglob(f"{prefix}/{path}/**/*", recursive=True)) for path in paths])
    data_files = defaultdict(list)
    for filename in files:
        target_dir = relpath(dirname(filename), prefix)
        data_files[target_dir].append(filename)

    return list(data_files.items())


def get_python_lib():
    """
    Returns absolute path to libpythonX.YZ.so on linux, libpythonX.Y.dylib on macOS or pythonXY.lib on windows.
    """
    if is_win:
        version_string = f"{sys.version_info[0]}{sys.version_info[1]}"
        python_lib = expandvars(
            f"%LOCALAPPDATA%\\Programs\\Python\\Python{version_string}\\libs\\python{version_string}.lib"
        )
    elif is_darwin:
        version_string = f"{sys.version_info[0]}.{sys.version_info[1]}"
        python_lib = f"{sys.prefix}/lib/x86_64-linux-gnu/libpython{version_string}.dylib"
    else:
        version_string = f"{sys.version_info[0]}.{sys.version_info[1]}{sys.abiflags}"
        python_lib = f"/usr/lib/x86_64-linux-gnu/libpython{version_string}.so.1.0"
    assert exists(python_lib)
    return python_lib


def get_python_include_dir():
    if is_win:
        include_dir = f"{sys.prefix}\\include"
    else:
        version_string = f"{sys.version_info[0]}.{sys.version_info[1]}{sys.abiflags}"
        include_dir = f"{sys.prefix}/include/python{version_string}"

    assert exists(include_dir)
    return include_dir


def get_lib_dir(relative=False):
    """
    Returns path to lib dir.
    """
    if is_win:
        lib = f"Lib"
    else:
        lib = f"lib/python{sys.version_info[0]}.{sys.version_info[1]}"

    if not relative:
        lib = join(sys.prefix, lib)
        assert exists(lib)

    return lib


def get_site_packages_dir():
    """
    Returns absolute path to site packages dir.
    """
    site_packages = join(get_lib_dir(), "site-packages")

    assert exists(site_packages)
    return site_packages


def get_vcvarsall():
    path = expandvars(
        "%PROGRAMFILES(x86)%\\Microsoft Visual Studio\\2017\\BuildTools\\VC\\Auxiliary\\Build\\vcvarsall.bat"
    )
    assert exists(path)
    return path


def get_include_dir():
    """Returns the path to the Python environment's include dir."""
    return get_paths()['include']
