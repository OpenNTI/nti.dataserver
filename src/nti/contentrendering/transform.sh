#!/bin/bash

MYPATH=`dirname $0`
ROOT=$MYPATH/../../..
export XHTMLTEMPLATES=$ROOT/renderers
# If we cannot locate the renderer templates,
# then we wind up with only partial HTML files
# (i.e., the <html> tag is missing, all the stuff that comes from
# the default-layout.)
if [ -x `which greadlink` ]; then
	export XHTMLTEMPLATES=`greadlink -f $XHTMLTEMPLATES`
elif [ -x /opt/local/bin/greadlink ]; then
	export XHTMLTEMPLATES=`/opt/local/bin/greadlink -f $XHTMLTEMPLATES`
else 
	echo "No way to resolve relative paths; render may fail"
fi
export PYTHONPATH=$MYPATH:$ROOT/python/:$PYTHONPATH


${PYTHON:-python2.7} -m nti.contentrendering.aopstoxml $1 $2

