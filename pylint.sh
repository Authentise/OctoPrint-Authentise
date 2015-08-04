set -x
PROJECT=octoprint_authentise
SCRIPTS=""
if [ -z "$1" ]; then
    FILES="$(find $PROJECT -maxdepth 3 -name "*.py" -print) $SCRIPTS $(find tests -maxdepth 3 -name "*.py" -print)"
else
    FILES="$1"
    echo "linting $FILES"
fi
pylint --rcfile=tests/pylint.cfg $FILES --reports=no
