#!/usr/bin/env python
"""
Convenient functions for creating simple math doms from latex expressions.
"""
from zope import component
import sys

from nti.assessment import interfaces
import nti.openmath as openmath

import tempfile
import StringIO

import plasTeX

from plasTeX.TeX import TeX


def _buildDomFromString(docString):
	document = plasTeX.TeXDocument()
	strIO = StringIO.StringIO(docString)
	strIO.name = 'temp'
	tex = TeX(document,strIO)
	document.userdata['jobname'] = 'temp'
	document.userdata['working-dir'] = tempfile.gettempdir()
	tex.parse()
	return document

def _simpleLatexDocument(maths):
	doc = r"""\documentclass[12pt]{article} \usepackage{amsmath} \begin{document} """
	mathString = '\n'.join( [str(m) for m in maths] )
	doc = doc + '\n' + mathString + '\n\\end{document}'
	return doc

def _mathTexToDOMNodes(maths):
	doc = _simpleLatexDocument(maths)
	dom = _buildDomFromString(doc)

	return dom.getElementsByTagName('math')

def _response_text_to_latex(response):
	# Experimentally, plasTeX sometimes has problems with $ display math
	# We haven't set seen that problem with \( display math
	if response.startswith( '$' ):
		response = response[1:-1]

	if openmath.OMOBJ in response or openmath.OMA in response:
		response = openmath.OpenMath2Latex().translate( response )
	else:
		if response.startswith( '\\text{' ) and response.endswith( '}' ):
			response = response[6:-1]

		response = response.replace( '\\left(', '(' )
		response = response.replace( '\\right)', ')' )
		# old versions of mathquill emit \: instead of \;
		response = response.replace( r'\:', ' ' )
		# However, plasTeX does not understand \;
		response = response.replace( r'\;', ' ' )
		response = "\\(" + response + "\\)"
	return response

def convert( response ):
	cache_attr = '_v_latexplastexconverter_cache'
	cached_value = getattr( response, cache_attr, None )
	if not cached_value or cached_value[0] != response.value:
		response_doc = _response_text_to_latex( response.value )
		dom = _mathTexToDOMNodes( ( response_doc, ) )
		if len(dom) == 1:
			cached_value = (response.value, dom[0])
			setattr( response, cache_attr, cached_value )

	return cached_value[1] if cached_value else None

def factory( solution, response ):
	if response.value:
		return sys.modules[__name__]

component.moduleProvides( interfaces.IResponseToSymbolicMathConverter )
