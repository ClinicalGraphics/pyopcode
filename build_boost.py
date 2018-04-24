import logging
import subprocess
from multiprocessing import cpu_count
from os.path import abspath, exists

from setup_utils import get_include_dir, get_vcvarsall, is_win


def call(cmd, **kwargs):
    cwd = f"{kwargs['cwd']}> " if 'cwd' in kwargs else ""
    msg = f"spawning subprocess: {cwd}{cmd}"
    logging.info(msg)
    subprocess.run(cmd, shell=True, check=True, **kwargs)


def main():
    build_prefix = abspath("build_boost")
    pkg_prefix = abspath("pyopcode")
    toolset = "gcc"
    sh_ext = "sh"
    sh_prefix = "./"
    if is_win:
        call(f"\"{get_vcvarsall()}\" amd64")
        toolset = "msvc"
        sh_ext = "bat"
        sh_prefix = ""
    if not exists(build_prefix):
        call(f"{sh_prefix}bootstrap.{sh_ext}", cwd="boost_1_67_0")
    call(f"{sh_prefix}b2"
         f" toolset={toolset}"
         " address-model=64"
         " link=shared"
         " variant=release"
         " threading=multi"
         " runtime-link=shared"
         f" include={get_include_dir()}"
         " --with-python"
         f" -j{cpu_count()}"
         " install"
         f" --prefix=\"{build_prefix}\""
         f" --libdir=\"{pkg_prefix}\"",
         cwd="boost_1_67_0")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    main()
