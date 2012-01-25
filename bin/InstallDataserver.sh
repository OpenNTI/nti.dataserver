#!/bin/bash


if [ -z "$WORKON_HOME" ]; then
	echo "Must have a location to put virtualenv. Set WORKON_HOME."
	exit 1
fi
# make sure virtualenv is on the path
export PATH=/opt/local/Library/Frameworks/Python.framework/Versions/2.7/bin:$PATH

if [ -z `which virtualenvwrapper.sh` ]; then
	echo "Installing virtualenvwrapper. You may be prompted for a password"
	sudo easy_install-2.7 virtualenvwrapper
fi

source `which virtualenvwrapper.sh`

VENV=${1:-nti.dataserver}
echo "Using virtual environment $VENV"

mkvirtualenv --distribute $VENV

echo "Switching to environment"
workon $VENV

echo "Upgrading pip"
pip install --upgrade git+https://github.com/pypa/pip.git#egg=pip
#pip install --upgrade pip

export CFLAGS="-I/opt/local/include -L/opt/local/lib"

echo "Installing pyzmq"
pip install cython
pip install --install-option="--zmq=/opt/local" pyzmq

PROJECT_PARENT=${2:-~/Projects}
echo "Checking project out to $PROJECT_PARENT/NextThoughtPlatform"

mkdir -p $PROJECT_PARENT
svn co https://svn.nextthought.com/repository/NextThoughtPlatform/trunk $PROJECT_PARENT/NextThoughtPlatform

cd $PROJECT_PARENT/NextThoughtPlatform/nti.dataserver

pip install -r requirements.txt

python setup.py develop

echo "Done."
echo "Be sure to include the following lines in your .bash_profile:"
echo
echo "export WORKON_HOME='$WORKON_HOME'"
echo "source /opt/local/Library/Frameworks/Python/Versions/2.7/bin/virtualenvwrapper.sh"
echo "workon $VENV #optional"
echo
