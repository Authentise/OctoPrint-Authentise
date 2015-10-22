# coding=utf-8
import contextlib
import imp
import os
import re
import subprocess

from setuptools import setup

try:
    import octoprint_setuptools
except: #pylint: disable=bare-except
    print("Could not import OctoPrint's setuptools, are you sure you are running that under "
        "the same python installation that OctoPrint is installed under?")
    import sys
    sys.exit(-1)

########################################################################################################################
### Do not forget to adjust the following variables to your own plugin.

# The plugin's identifier, has to be unique
plugin_identifier = "authentise"

# The plugin's python package, should be "octoprint_<plugin identifier>", has to be unique
plugin_package = "octoprint_authentise"

# The plugin's human readable name. Can be overwritten within OctoPrint's internal data via __plugin_name__ in the
# plugin module
plugin_name = "OctoPrint-Authentise"

# The plugin's description. Can be overwritten within OctoPrint's internal data via __plugin_description__ in the plugin
# module
plugin_description = """Authenitse Octoprint Integration"""

# The plugin's author. Can be overwritten within OctoPrint's internal data via __plugin_author__ in the plugin module
plugin_author = "Authentise, Inc."

# The plugin's author's mail address.
plugin_author_email = "engineering@authentise.com"

# The plugin's homepage URL. Can be overwritten within OctoPrint's internal data via __plugin_url__ in the plugin module
plugin_url = "https://github.com/authentise/OctoPrint-Authentise"

# The plugin's license. Can be overwritten within OctoPrint's internal data via __plugin_license__ in the plugin module
plugin_license = "AGPLv3"

# Any additional requirements besides OctoPrint should be listed here
plugin_requires = [
    'requests==2.8.1',
]

extra_requires = {
    'develop': [
        'pytest==2.7.2',
        'pytest-mock==0.7.0',
        'httpretty==0.8.10',
        'pylint==1.4.4',
        'isort==4.0.0',
        'ipython==3.2.1',
    ]
}

### --------------------------------------------------------------------------------------------------------------------
### More advanced options that you usually shouldn't have to touch follow after this point
### --------------------------------------------------------------------------------------------------------------------

# Additional package data to install for this plugin. The subfolders "templates", "static" and "translations" will
# already be installed automatically if they exist.
plugin_additional_data = []

# Any additional python packages you need to install with your plugin that are not contains in <plugin_package>.*
plugin_addtional_packages = []

# Any python packages within <plugin_package>.* you do NOT want to install with your plugin
plugin_ignored_packages = []

# Additional parameters for the call to setuptools.setup. If your plugin wants to register additional entry points,
# define dependency links or other things like that, this is the place to go. Will be merged recursively with the
# default setup parameters as provided by octoprint_setuptools.create_plugin_setup_parameters using
# octoprint.util.dict_merge.
#
# Example:
#     plugin_requires = ["someDependency==dev"]
#     additional_setup_parameters = {"dependency_links": ["https://github.com/someUser/someRepo/archive/master.zip#egg=someDependency-dev"]}
additional_setup_parameters = {}

########################################################################################################################

VERSION_FILE = 'octoprint_authentise/version.py'

def _get_output_or_none(args):
    def _check_output(*popenargs, **kwargs):
        r"""Run command with arguments and return its output as a byte string.
        Backported from Python 2.7 as it's implemented as pure python on stdlib.
        >>> check_output(['/usr/bin/python', '--version'])
        Python 2.6.2
        """
        process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
        output, dummy_err = process.communicate()
        retcode = process.poll()
        if retcode:
            cmd = kwargs.get("args")
            if cmd is None:
                cmd = popenargs[0]
            error = subprocess.CalledProcessError(retcode, cmd)
            error.output = output
            raise error
        return output

    try:
        return _check_output(args).decode('utf-8').strip()
    except subprocess.CalledProcessError:
        return None

def _get_git_description():
    return _get_output_or_none(['git', 'describe'])

def _get_git_branches_for_this_commit():
    branches = _get_output_or_none(['git', 'branch', '-r', '--contains', 'HEAD'])
    split = branches.split('\n') if branches else []
    return [branch.strip() for branch in split]

def _is_on_releasable_branch(branches):
    return any(['origin/master' == branch or branch.startswith('origin/hotfix') for branch in branches])

def _git_to_version(git):
    match = re.match(r'(?P<tag>[\d\.]+)-(?P<offset>[\d]+)-(?P<sha>\w{8})', git)
    if not match:
        version = git
    else:
        version = "{tag}.post0.dev{offset}".format(**match.groupdict())
    print("Calculated {0} version '{1}' from git description '{2}'".format(plugin_package, version, git))
    return version

@contextlib.contextmanager
def write_version():
    git_description = _get_git_description()
    git_branches = _get_git_branches_for_this_commit()
    version = _git_to_version(git_description) if git_description else None
    if git_branches and not _is_on_releasable_branch(git_branches):
        print("Forcing version to 0.0.1 because this commit is on branches {0} and not a whitelisted branch".format(git_branches))
        version = '0.0.1'
    if version:
        with open(VERSION_FILE, 'r') as version_file:
            old_contents = version_file.read()
        with open(VERSION_FILE, 'w') as version_file:
            version_file.write('VERSION = "{0}"\n'.format(version))
    yield
    if version:
        with open(VERSION_FILE, 'w') as version_file:
            version_file.write(old_contents)

def get_version():
    basedir = os.path.abspath(os.path.dirname(__file__))
    version = imp.load_source('version', os.path.join(basedir, plugin_package, 'version.py'))
    return version.VERSION

with write_version():
    setup_parameters = octoprint_setuptools.create_plugin_setup_parameters(
            identifier=plugin_identifier,
            package=plugin_package,
            name=plugin_name,
            version=get_version(),
            description=plugin_description,
            author=plugin_author,
            mail=plugin_author_email,
            url=plugin_url,
            license=plugin_license,
            requires=plugin_requires,
            extra_requires=extra_requires,
            additional_packages=plugin_addtional_packages,
            ignored_packages=plugin_ignored_packages,
            additional_data=plugin_additional_data
    )

    if len(additional_setup_parameters):
        from octoprint.util import dict_merge
        setup_parameters = dict_merge(setup_parameters, additional_setup_parameters)

    setup(**setup_parameters)
