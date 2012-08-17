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
pip install --install-option="--zmq=/opt/local" "pyzmq>=2.2.0"

PROJECT_PARENT=${2:-~/Projects}
echo "Checking project out to $PROJECT_PARENT/NextThoughtPlatform"

if [ -d "$PROJECT_PARENT/NextThoughtPlatform" ]; then
	cd $PROJECT_PARENT/NextThoughtPlatform
	svn up
else
	mkdir -p $PROJECT_PARENT
	svn co https://svn.nextthought.com/repository/NextThoughtPlatform/trunk $PROJECT_PARENT/NextThoughtPlatform
fi

cd $PROJECT_PARENT/NextThoughtPlatform/nti.dataserver

# NOTE: On AWS, you will need to yum install libxml2-devel and libxslt-devel,
# and probably add /usr/includ/libxml2/ to CFLAGS

pip install -r requirements.txt

export INSTALL_EXTRAS="True"

if [ "$INSTALL_EXTRAS" ]; then

	echo "Installing extras"

	# create a temo work directory
	TMPWK_DIR=`mktemp -d -t tmpwork`
	chmod 777 $TMPWK_DIR
	export PATH=$TMPWK_DIR:$PATH

	# set the "UMFPACK" variable to install scipy
	export UMFPACK="None"

	# make sure we have suitable fortran compiler to install scipy
	pkgs=( g95 gfortran `seq -f "gfortran-mp-4.%g" 4 7` )
	for p in "${pkgs[@]}"
	do
		cmp=`which $p`
		if [ -n "$cmp" ]; then
			ln -s $cmp $TMPWK_DIR/gfortran
			break
		elif [ -f "/opt/local/bin/$p" ]; then
			ln -s "/opt/local/bin/$p" $TMPWK_DIR/gfortran
			break
		fi
	done

	# install extra packages
	extrap_pkgs=(pyyaml numpy matplotlib scipy py rtf2xml)
	for p in "${extrap_pkgs[@]}"
	do
		echo "Installing $p"
		pip install -U ${p}
	done

	# clean
	rm -rf $TMPWK_DIR
fi

python setup.py dev

echo "Done."
echo "Be sure to include the following lines in your .bash_profile:"
echo
echo "export WORKON_HOME='$WORKON_HOME'"
echo "source /opt/local/Library/Frameworks/Python/Versions/2.7/bin/virtualenvwrapper.sh"
echo "workon $VENV #optional"
echo
