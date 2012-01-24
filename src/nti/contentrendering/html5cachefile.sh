#!/bin/bash

MYPATH=`dirname $0`

${PYTHON:-python2.7} $MYPATH/html5cachefile.py $*

