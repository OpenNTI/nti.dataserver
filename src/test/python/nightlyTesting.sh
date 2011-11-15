#!/bin/bash

function pause()
{
   read -p "$*"
}

export PATH=/opt/local/bin:$PATH
export TMPDIR=/tmp
CHECKOUT_DIR=`mktemp -d -t nightly`

cd $CHECKOUT_DIR
echo `pwd`

# Checkout the source

echo "Checking out source..."
svn co -q https://svn.nextthought.com/repository/AoPS/trunk AoPS
svn co -q https://svn.nextthought.com/repository/NextThoughtPlatform/trunk/ NextThoughtPlatform

# Install the dictionary file

echo "Installing the dictionary file..."
TEST_DIR=`pwd`/NextThoughtPlatform/src/test/python
PYTHONPATH=`pwd`/NextThoughtPlatform/src/main/python
mkdir $PYTHONPATH/wiktionary/
cp ~/bin/dict.db $PYTHONPATH/wiktionary/

# Setup a location for the dataserver
mkdir Data
export DATASERVER_DIR=`pwd`/Data
export TEST_WAIT=10
#export DATASERVER_NO_REDIRECT=1
LOG=/tmp/lastNightlyTesting.txt
export PATH=/opt/local/Library/Frameworks/Python.framework/Versions/2.7/bin:$PATH

mkdir -p $DATASERVER_DIR

function stop_daemons()
{
	for i in $1/*.zconf.xml; do
		zdaemon -C $i stop
	done
}

function clean_data()
{
	rm -rf $1
	mkdir -p $1
}

#Let 'er rip!
date
export PYTHONPATH
cd $PYTHONPATH

echo "Executing ServerTest_v2..."
python2.7 $TEST_DIR/ServerTest_v2.py > $LOG 2>&1
stop_daemons $DATASERVER_DIR 
clean_data $DATASERVER_DIR

echo "Executing ServerTest_v3_quizzes..."
python2.7 $TEST_DIR/ServerTest_v3_quizzes.py >> $LOG 2>&1
stop_daemons $DATASERVER_DIR 
clean_data $DATASERVER_DIR

echo "Executing Integration tests..."
python2.7 $TEST_DIR/run_integration_tests.py --use_coverage >> $LOG 2>&1
stop_daemons $DATASERVER_DIR 
clean_data $DATASERVER_DIR

COVERDIR=${COVERDIR:-/Library/WebServer/Documents/cover-reports}
if [ -d $COVERDIR ]; then
	COVEROPT="--cover-html-dir=$COVERDIR"
fi

nosetests -d --with-coverage --cover-html $COVEROPT --cover-inclusive --cover-package=nti,socketio,geventwebsocket,wiktionary,context >> $LOG 2>&1

stop_daemons $DATASERVER_DIR 
cat $LOG
if [ -d $COVERDIR ]; then
	cp $LOG $COVERDIR
fi

# Cleanup

cd ~
rm -rf $CHECKOUT_DIR
date
