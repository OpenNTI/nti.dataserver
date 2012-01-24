#!/bin/bash

MYPATH=`dirname $0`

${PYTHON:-python2.7} $MYPATH/mirror.py $1 $2

