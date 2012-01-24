#!/bin/bash

ORIG_PATH=`pwd`
cd "$(dirname $0)"
MYPATH=`pwd`
cd "$ORIG_PATH"

export XHTMLTEMPLATES=$MYPATH/../renderers
export PYTHONPATH=$MYPATH:$MYPATH/../plastex/:$PYTHONPATH

${PYTHON:-python2.7} $MYPATH/../plastex/plasTeX/plastex --xml --theme=AoPS --transparent-images --save-image-file --split-level=1 --image-compiler=pdflatex --imager=gspdfpng2 --enable-image-cache --vector-imager=pdf2svg --dir rendered $1

