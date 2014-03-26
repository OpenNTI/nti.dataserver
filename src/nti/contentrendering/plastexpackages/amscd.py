# -*- coding: utf-8 -*-
"""
Partial support for the amscd package. This allows for parsing the environment 
and assumes that the actual processing will be handed off to either pdfLaTeX 
or MathJax.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from plasTeX.Base.LaTeX.Arrays import Array

class cd(Array):
	macroName = 'CD'

