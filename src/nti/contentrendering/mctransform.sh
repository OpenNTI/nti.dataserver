#!/bin/bash

MYPATH=`dirname $0`
export XHTMLTEMPLATES=$MYPATH/../renderers
export PYTHONPATH=$MYPATH:$MYPATH/../plastex/

${PYTHON:-python2.7} $MYPATH/mctransform.py $*

