# -*- coding: utf-8 -*-
"""
Partial support for the amscd package. This allows for parsing the environment 
and assumes that the actual processing will be handed off to either pdfLaTeX 
or MathJax.

$Id:$
"""

from plasTeX.Base.LaTeX.Arrays import Array

class cd(Array):
	macroName = 'CD'

