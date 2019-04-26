#!/bin/sh

# This file was originally taken from the sara-nl Grid Project docs:
# https://github.com/sara-nl/griddocs
# but was modified so heavily that little remains of the original

set -e

do_help() {
  cat >&2 <<HELPSTR
Usage: ${0} {docker|here} conf.py [output_dir]

{docker|here}   "here": run the sphinx build immediately.
                "docker": setup a docker container and invoke this script  with
                  "here"in the container.
conf.py         Path to the sphinx config.
output_dir      Where to place the build results (defaults to a _build dir
                in the same directory as conf.py.

BIG WARNING: To better emulate RTD, this script will run "git clean -dff". It
is recommended to make a local clone to avoid nasty surprises.

Env variables:
  RTD_DOCKER_IMAGE: name of the docker image (default readthedocs/build:latest)
  PIP_CACHE: directory to use as pip cache (default is ${HOME}/.cache/pip)
HELPSTR
}

do_additions() {
  cat <<RTDADDITION
import importlib
import sys
import os.path
from six import string_types

from sphinx import version_info

# Get suffix for proper linking to GitHub
# This is deprecated in Sphinx 1.3+,
# as each page can have its own suffix
if globals().get('source_suffix', False):
    if isinstance(source_suffix, string_types):
        SUFFIX = source_suffix
    elif isinstance(source_suffix, (list, tuple)):
        # Sphinx >= 1.3 supports list/tuple to define multiple suffixes
        SUFFIX = source_suffix[0]
    elif isinstance(source_suffix, dict):
        # Sphinx >= 1.8 supports a mapping dictionary for mulitple suffixes
        SUFFIX = list(source_suffix.keys())[0]  # make a ``list()`` for py2/py3 compatibility
    else:
        # default to .rst
        SUFFIX = '.rst'
else:
    SUFFIX = '.rst'

# Add RTD Static Path. Add to the end because it overwrites previous files.
if not 'html_static_path' in globals():
    html_static_path = []
if os.path.exists('_static'):
    html_static_path.append('_static')

# Add RTD Theme only if they aren't overriding it already
using_rtd_theme = (
    (
        'html_theme' in globals() and
        html_theme in ['default'] and
        # Allow people to bail with a hack of having an html_style
        'html_style' not in globals()
    ) or 'html_theme' not in globals()
)
if using_rtd_theme:
    theme = importlib.import_module('sphinx_rtd_theme')
    html_theme = 'sphinx_rtd_theme'
    html_style = None
    html_theme_options = {}
    if 'html_theme_path' in globals():
        html_theme_path.append(theme.get_html_theme_path())
    else:
        html_theme_path = [theme.get_html_theme_path()]

if globals().get('websupport2_base_url', False):
    websupport2_base_url = 'https://readthedocs.org/websupport'
    websupport2_static_url = 'https://assets.readthedocs.org/static/'


#Add project information to the template context.
context = {
    'using_theme': using_rtd_theme,
    'html_theme': html_theme,
    'current_version': "unknown",
    'version_slug': "unknown",
    'MEDIA_URL': "https://media.readthedocs.org/",
    'STATIC_URL': "https://assets.readthedocs.org/static/",
    'PRODUCTION_DOMAIN': "readthedocs.org",
    'versions': [
    ("unknown", "/en/unknown/"),
    ],
    'downloads': [
    ],
    'subprojects': [
    ],
    'slug': 'unknown',
    'name': u'unknown',
    'rtd_language': u'en',
    'programming_language': u'c',
    'canonical_url': '',
    'analytics_code': 'None',
    'single_version': False,
    'conf_py_path': '',
    'api_host': 'https://readthedocs.org',
    'github_user': '',
    'github_repo': '',
    'github_version': '',
    'display_github': True,
    'bitbucket_user': 'None',
    'bitbucket_repo': 'None',
    'bitbucket_version': '',
    'display_bitbucket': False,
    'gitlab_user': 'None',
    'gitlab_repo': 'None',
    'gitlab_version': '',
    'display_gitlab': False,
    'READTHEDOCS': True,
    'using_theme': (html_theme == "default"),
    'new_theme': (html_theme == "sphinx_rtd_theme"),
    'source_suffix': SUFFIX,
    'ad_free': False,
    'user_analytics_code': '',
    'global_analytics_code': '',
    'commit': '',
}




if 'html_context' in globals():

    html_context.update(context)

else:
    html_context = context

# Add custom RTD extension
if 'extensions' in globals():
    # Insert at the beginning because it can interfere
    # with other extensions.
    # See https://github.com/rtfd/readthedocs.org/pull/4054
    extensions.insert(0, "readthedocs_ext.readthedocs")
else:
    extensions = ["readthedocs_ext.readthedocs"]
RTDADDITION
}

not_relative() {
  test "${1##/}" != "${1}"
}

# Parse the parameters
if [ -f "${2}" ]; then
  _CONF_PY="${2}"
else
  echo "Config file not found: ${2}" >&2
  do_help
  exit 1
fi

_SRC_DIR="$(dirname "${_CONF_PY}")"

REPO_DIR="$(git -C "${_SRC_DIR}" rev-parse --show-toplevel)"

SRC_DIR="$(realpath --relative-base="${REPO_DIR}" "${_SRC_DIR}")"
CONF_PY="$(realpath --relative-base="${REPO_DIR}" "${_CONF_PY}")"

_OUTPUT_DIR="${3:-${SRC_DIR}/_build}"
OUTPUT_DIR="$(realpath --relative-base="${REPO_DIR}" "${_OUTPUT_DIR}")"

if not_relative "${SRC_DIR}" ; then
  echo "The output dir mus be inside the repo" >&2
  exit 2
fi

_PIP_CACHE="${PIP_CACHE:-${HOME}/.cache/pip}"

restore_conf() {
  git checkout -- "${REPO_DIR}/${CONF_PY}"
}

if [ "${1}" = here ] ; then
  #umask 0002

  if [ -n "${HOST_UID}" ] ; then
    #apt-get install -y python3-venv
    set -x
    groupadd -g"${HOST_GID}" rtduser
    useradd -m -u "${HOST_UID}" -N -g "${HOST_GID}" rtduser
    unset HOST_UID
    unset HOST_GID
    exec runuser -g rtduser -u rtduser -- "${0}" "${@}"
  fi

  python3.7 -mvirtualenv ~/venv
  . ~/venv/bin/activate

  set -x
  export READTHEDOCS=True

  cd "${REPO_DIR}"

  git checkout -f HEAD
  git clean -d -f -f
  git submodule sync
  git submodule update --init --force

  pip install --upgrade --cache-dir /pip-cache -I \
    'Pygments==2.3.1' 'setuptools<41' 'docutils==0.14' 'mock==1.0.1' 'pillow==5.4.1' \
    'alabaster>=0.7,<0.8,!=0.7.5' 'commonmark==0.8.1' 'recommonmark==0.5.0' 'sphinx<2' \
    'sphinx-rtd-theme<0.5' 'readthedocs-sphinx-ext<0.6'

  pip install --cache-dir /pip-cache -r .rtd-requirements.txt

  cd "${SRC_DIR}"
  _OUT_DIR_R="$(realpath --relative-to="${_SRC_DIR}" "${_OUTPUT_DIR}")"

  trap restore_conf EXIT

  do_additions >> "${REPO_DIR}/${CONF_PY}"

  ~/venv/bin/sphinx-build -T -b readthedocs -d "${_OUT_DIR_R}/doctrees-readthedocs" -D language=en . "${_OUT_DIR_R}/html"

  exit
elif [ "${1}" != docker ] ; then
  echo "Unknown command ${1}" >&2
  do_help
  exit 1
fi


_RTD_DOCKER_IMAGE="${RTD_DOCKER_IMAGE:-readthedocs/build:latest}"

set -x
sudo docker run --rm --volume "${REPO_DIR}:/source" \
    --volume "${_PIP_CACHE}:/pip-cache" \
    --volume "$(realpath "${0}")":/build.sh \
    -e PIP_CACHE=/pip-cache -e HOST_UID="${UID}" -e HOST_GID="$(id -g)" \
    -u root \
    "${_RTD_DOCKER_IMAGE}" \
    /bin/sh /build.sh here "/source/${CONF_PY}" "/source/${OUTPUT_DIR}"
