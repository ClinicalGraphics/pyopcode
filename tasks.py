from __future__ import absolute_import, division, print_function

import os
import shutil
import subprocess
import sys
import traceback
import multiprocessing

from invoke import run, task
import requests
import yaml

import pkg_conf

# variables used to build documentation and package according to OS
on_win32 = sys.platform.startswith("win")
on_linux = sys.platform.startswith("linux")
on_osx = sys.platform.startswith("darwin")
on_unix = on_linux or on_osx


def _print(message):
    print("[INVOKE] {}".format(message))


def _exit(message):
    sys.exit("[INVOKE QUITTING] {}".format(message))


def _confirm(prompt='Are you sure?', error='Cancelled.'):
    """
    Prompt the user to confirm.
    """
    response = input("{} Type 'y' and hit enter to continue. Anything else will cancel.\n".format(prompt)).lower()

    if response != "y":
        _exit(error)

    return True

@task
def build(python=None, inplace=False):
    """
    Builds the conda package
    """
    _print("Building your package now")

    if inplace:
        # fake conda-build envvars
        env = {
            'PY_VER': '{}.{}'.format(*sys.version_info[:2]),
            'ARCH': '64',
            'PREFIX': sys.exec_prefix,
            'SP_DIR': "{0}{1}Lib{1}site-packages".format(sys.exec_prefix, os.sep),
        }
        # make sure we activate our build tools on windows automatically
        if on_win32:
            # importing setuptools patches distutils so that it knows how to find VC for python 2.7
            # Leverage the hard work done by setuptools/distutils to find vcvarsall
            import setuptools
            from distutils.msvc9compiler import find_vcvarsall
            if sys.version_info[:2] == (3, 5):
                vcvarsall = find_vcvarsall(14)
                env['CMAKE_GENERATOR'] = 'Visual Studio 14 2015 Win64'
            elif sys.version_info[:2] == (2, 7):
                vcvarsall = find_vcvarsall(9)
                env['CMAKE_GENERATOR'] = 'Visual Studio 9 2008 Win64'
            else:
                _exit("version of python not supported")
            cmd = "activate {}".format(os.path.basename(sys.exec_prefix))
            cmd += ' && "{}" amd64'.format(vcvarsall)
            cmd += ' && call "conda-recipe/bld.bat"'
        # set the environment, because invoke can't do it for some reason
        _print("Using fake conda-build environment: {}".format(env))
        for k, v in env.items():
            os.environ[k] = v
        # now run the build
        run(cmd, echo=True, shell=True)
    else:
        # build with the required anaconda channels in the environment.yml
        command = "conda build conda-recipe --no-anaconda-upload --quiet " +\
                  ' '.join(['-c {}'.format(c) for c in pkg_conf.get_channels()])
        if python is not None:
            command = command + ' --python ' + python
        run(command, pty=on_unix)


@task
def test():
    """
    Runs the test suite
    """
    pkg_name = pkg_conf.PKG_ROOT
    run("py.test --pyargs {}".format(pkg_name))


@task
def lint():
    """
    Lints the source code
    """
    run("flake8 {}".format(pkg_conf.PKG_ROOT))
    # make sure this command is run regularly as well
    _environment_and_recipe_consistency()


@task
def precommit():
    """
    Runs all precommit checks in order
    """
    _print("Linting...")
    lint()
    _print("Linting passed! Testing...")
    test()
    _print("Testing passed! Doccing...")
    docs(quiet=True)


@task(name="build-ci")
def build_ci(branch=None, revision=None, token=None, provider='appveyor'):
    """
    Triggers a build on CI
    """
    # validate provider selection
    if provider not in ['appveyor']:
        # FIXME would be nice to add CodeShip here later
        _exit("Selected provider is not supported.")

    # get revision info if it's not provided
    hg_info = _get_hg_info()
    if branch is None and revision is None:
        branch = hg_info['branch']
        revision = hg_info['id']

    # check dirtiness
    if revision is not None and _hg_rev_is_dirty(revision):
        _exit("Cannot trigger a remote CI build for a dirty revision (you have local changes)")

    # FIXME we should also prevent triggering a build for a "draft", or "local", revision, but that's hard :/

    # get API token
    if token is None:
        env_var = "CG_CI_TOKEN_{}".format(provider).upper()
        token = os.environ.get(env_var, None)
        if token is None:
            _exit(
                "You must provide an API token, either through --token or the environment variable {}".format(env_var))

    # make the request
    _print("Requesting build...")
    if provider == 'appveyor':
        request_body = {
            'accountName': 'clinicalgraphics',
            'projectSlug': 'scikit-clinicalgraphics',
        }

        if branch is not None:
            request_body['branch'] = branch
        if revision is not None:
            request_body['commitId'] = revision

        requests.post('https://ci.appveyor.com/api/builds', headers={
            'Authorization': 'Bearer {}'.format(token),
        }, json=request_body).raise_for_status()

    _print("Build requested!")


# @task
# def changelog():
#     # TODO: update changelog
#     pass


def _browse(url):
    if on_win32:
        run('explorer "{}"'.format(url), hide='stdout')
    elif on_unix:
        run('xdg-open "{}"'.format(url), hide='stdout')
    else:
        raise NotImplementedError("Browsing is not supported for this OS")


def _environment_and_recipe_consistency():
    """Notify if environment.yml and meta.yml appear to be inconsistent"""
    # get recipe yaml
    recipe = pkg_conf.get_recipe_meta()
    # custom loading of environment.yml
    with open(os.path.join(pkg_conf.ABS_REPO_ROOT, 'environment.yml'), "r") as infile:
        environment = infile.read()
        environment = yaml.load(environment.split('# dev')[0])  # only take the first part of environment file

    reformatted_environment_lines = []
    msg = "dependency '{}' does not appear to be present as such in recipe: requirements: {}:"
    for line in environment['dependencies']:
        # note; conda build and conda env have subtly different syntax for pinning to a fixed version
        reformat_line = line.replace(' =', ' ')
        reformatted_environment_lines.append(reformat_line)
        if reformat_line not in recipe['requirements']['build']:
            _exit(msg.format(line, 'build'))
        if reformat_line not in recipe['requirements']['run']:
            _exit(msg.format(line, 'run'))

    msg = "{} requirement '{}' does not appear to be present as such in environment file"
    for line in recipe['requirements']['run']:
        if line not in reformatted_environment_lines:
            _exit(msg.format('run', line))


@task(help={'quiet': "Do not open documentation index in browser after building."})
def docs(quiet=False, clean=False):
    """
    Build the documentation.
    """
    if not os.path.exists(pkg_conf.DOC_ROOT):
        _exit("Documentation root doesn't exist.")

    source_path = os.path.join(pkg_conf.DOC_ROOT, 'source')
    build_path = os.path.join(pkg_conf.DOC_ROOT, 'build')

    if clean and os.path.exists(build_path):
        _print("Clearing build directory.")
        shutil.rmtree(build_path)

    run("sphinx-build -q {} {}".format(source_path, build_path))

    if not quiet:
        _browse("file:///{}/{}/build/index.html".format(os.path.dirname(os.path.realpath(__file__)).replace("\\", "/"),
                                                        pkg_conf.DOC_ROOT))


def _hg_rev_is_dirty(rev):
    return "+" in rev


def _get_hg_info():
    """
    Checks if the current directory is under hg version control

    Returns current revision id if current directory is under hg version control, False if not.
    """
    id = subprocess.check_output(["hg", "identify", "--id"]).decode('utf-8').strip()
    branch = subprocess.check_output(["hg", "branch"]).decode('utf-8').strip()
    return {
        'branch': branch,
        'id': id,
        "dirty": _hg_rev_is_dirty(id),
    }


def _get_git_info():
    id = subprocess.check_output(["git", "status"]).decode('utf-8').strip()
    branch = subprocess.check_output(["git", "branch"]).decode('utf-8').strip()
    return {
        'branch': branch,
        'id': id,
        "dirty": "modified" in id,
        "default": "master" in branch
    }


def _assert_version_ok_git():
    info = _get_git_info()
    if info['dirty']:
        _exit("working directory is not clean, release cancelled")
    if not info['default']:
        _exit("not on default branch, release cancelled")


def _assert_version_ok_hg():
    hg_info = _get_hg_info()

    if hg_info['dirty']:
        _exit("working directory is not clean, release cancelled")


def _assert_release_ok():
    _assert_version_ok_git()

    current_version = pkg_conf.get_version()

    if 'dev' in current_version:
        _exit("dev version detected, release cancelled")


def _update_version(new_version_number, build_number):
    """
    Updates the version of the package and the conda recipe
    """
    # package
    with open("{}/__init__.py".format(pkg_conf.PKG_ROOT), "r") as infile:
        init_content = infile.readlines()

    i = 0
    for i, line in enumerate(init_content):
        if line.startswith("__version__ = "):
            break

    init_content[i] = "__version__ = '{}'".format(new_version_number)

    # Now we write it back to the file
    with open("{}/__init__.py".format(pkg_conf.PKG_ROOT), "w") as outfile:
        outfile.writelines(init_content)

    # conda recipe
    with open("conda-recipe/meta.yaml", "r") as infile:
        recipe_meta = yaml.load(infile)

    recipe_meta["package"]["version"] = new_version_number
    recipe_meta["build"]["number"] = build_number

    with open("conda-recipe/meta.yaml", "w") as outfile:
        outfile.write(yaml.safe_dump(recipe_meta, default_flow_style=False, allow_unicode=True))

    _print("Updated the version number to {}".format(new_version_number))


@task(name='version',
      help={
          "major": "Bump the major version number, e.g. from 0.0.0 to 1.0.0. Use it when you introduce breaking changes.",
          "minor": "Bump the minor version number, e.g. from 0.0.0 to 0.1.0. Use it when you introduce new features, and maintain backwards compatibility.",
          "patch": "Bump the patch version number, e.g. from 0.0.0 to 0.0.1. Use it when you only release bugfixes, and maintain backwards compatibility.",
          "rc": "Replace the dev label with an rc label to indicate that this is a production release candidate, e.g. from 0.0.dev0 to 0.0.rc0.",
          "release": "Leave out the dev label from the version number to indicate that this is a production release, e.g. from 0.0.dev0 to 0.0.0."})
def update_version(major=False, minor=False, patch=False, rc=False, release=False):
    """
    Bump the version of the package
    """
    _assert_version_ok_git()

    current_version = pkg_conf.get_version()
    current_build_number = pkg_conf.get_build_number()
    _print("Current version {}".format(current_version))
    _print("Current build number {}".format(current_build_number))

    # We strip out .dev if present, so we can parse the version number itself
    major_number, minor_number, patch_number = current_version.replace("dev", "").split(".")
    build_number = current_build_number

    if major:
        major_number = int(major_number) + 1
        minor_number = 0
        patch_number = 0
        build_number = 0
    elif minor:
        minor_number = int(minor_number) + 1
        patch_number = 0
        build_number = 0
    elif patch:
        patch_number = int(patch_number) + 1
        build_number = 0
    else:
        build_number += 1

    # By default we add dev to ours builds unless its a release
    label = "dev"
    if rc:
        label = "rc"
    elif release:
        label = ""

    version_number = "{}.{}.{}{}".format(major_number, minor_number, label, patch_number)

    # actually write to the recipe and package
    _update_version(version_number, build_number)

    # the version numbers in the package and recipe have been updated, so commit those changes first
    run('hg commit -m "Bumped version to {}_{}."'.format(version_number, build_number))


def _tag_hg_revision(revision_tag):
    """Tag current revision in mercurial."""
    hg_info = _get_hg_info()
    if hg_info['dirty']:
        _exit("Can't tag dirty revision.")

    # then tag the current revision
    if run("hg tag {}".format(revision_tag), warn=True):
        _print("Tag '{}' applied".format(revision_tag))
    else:
        # if tagging failed, apparently the tag already exists and someone is being silly
        _print("Tagging failed! Rolling back.")
        # the tag operation has already been rolled back
        # we should rollback the version number commit as well
        run('hg rollback')
        # and clean up the working dir so the updated files don't get committed accidentally anyway
        run('hg update -C')
        _exit("Are you sure the version you're going for doesn't already exist?")


def _tag_git_revision(revision_tag):
    """Tag current revision in mercurial."""
    git_info = _get_git_info()
    if git_info['dirty']:
        _exit("Can't tag dirty revision.")

    # then tag the current revision
    if run('git tag -a {} -m "{}"'.format(revision_tag, 'Tagged version {}'.format(revision_tag)), warn=True):
        _print("Tag '{}' applied".format(revision_tag))
    else:
        raise NotImplementedError('should do rollback here')
    run('git push origin')


@task(help={"yes": "Skip confirmation prompt."})
def release(yes=False):
    """
    Builds package and uploads to Anaconda.org
    We only allow releases from the production branch
    """
    _assert_version_ok_git()

    version = pkg_conf.get_version()

    _print("You are about to build and upload version {}, build {} of package {} to user {}".format(
        version, pkg_conf.get_build_number(), pkg_conf.PKG_NAME, pkg_conf.ANACONDA_USER))
    if yes or _confirm(prompt="Do you want to continue?"):
        cmd = "conda build conda-recipe --output"
        pkg_path = run(cmd, pty=on_unix, hide='stdout').stdout.strip()
        _print(pkg_path)

        cmd = "deactivate && conda build conda-recipe --no-anaconda-upload --quiet"
        if on_unix:
            cmd = "source " + cmd
        run(cmd, pty=on_unix)

        if os.path.exists(pkg_path):
            try:
                run("anaconda upload {} --user {}".format(pkg_path, pkg_conf.ANACONDA_USER))
                _tag_git_revision("v{}".format(version))
                return True
            except:
                traceback.print_exc()
                _print("Upload failed.")

        _print("Release failed.")
        return False
