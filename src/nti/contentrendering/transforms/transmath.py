#!/usr/bin/env python
# $Id$

from __future__ import print_function, unicode_literals

# Disable pylint warning about "too many methods" on the Command subclasses,
# and "deprecated string" module
#pylint: disable=R0904,W0402

import logging
logger = logging.getLogger(__name__)


from plasTeX import Node
import plasTeX.Base
import string

from zope import interface

from nti.contentrendering import interfaces
interface.moduleProvides(interfaces.IDocumentTransformer)


class _mathnode(plasTeX.Base.Command):
	origMathSource = None

	@property
	def source(self):
		return self.origMathSource

class mathname(_mathnode):
	nodeName = 'mathname'

class mathnumber(_mathnode):
	nodeName = 'mathnumber'


def transform(document):
	## document.context['mathangle'] = mathangle
	document.context['mathname'] = mathname
	document.context['mathname'] = mathnumber
	## document.context['mathline'] = mathline

	transformSimpleMath(document)
	transformSimpleNsuperscript(document)

def transformSimpleNsuperscript(document):
	nsuperscripts = []
	for name in ('nst', 'nnd', 'nrd', 'nth'):
		nsuperscripts.extend(document.getElementsByTagName(name))

	nsuperscriptsinmath = [node for node in nsuperscripts if node.parentNode.mathMode]

	for nsuperscript in nsuperscriptsinmath:
		#if our math parent only has one child and it is us
		if nsuperscript.parentNode.childNodes == [nsuperscript]:
			logger.info( 'Moving nsuperscript out of math environment %s', nsuperscript )
			mathsParent = nsuperscript.parentNode.parentNode
			mathsParent.replaceChild(nsuperscript, nsuperscript.parentNode)


def transformSimpleMath(document):
	""" Transform simple maths.	 Simple maths are math
	elements that have only text children """

	simpleMaths = [math for math in document.getElementsByTagName('math') \
				   if all( [ child.nodeType == Node.TEXT_NODE for child in math.childNodes ] )]

	simpleMaths = list(set(simpleMaths))

	for math in simpleMaths:
		text = math.textContent

		if not(text):
			# Remove any empty math nodes from the dom.	There are likely none;
			# their appearance is probably indicative of a problem in the source.
			logger.warning( 'Found empty math node %s (in %s ...)', math.toXML(), math.parentNode.source[:30] )
			math.parentNode.removeChild(math)
		elif all( [c in string.ascii_letters for c in text] ):
			# A node that's just a next name. Make it more expressive
			# for transform purposes. Previously we tried to infer
			# from the preceding text if this was an 'angle' or 'line'
			# but that was unreliable
			r = document.createElement( 'mathname' )
			r.attributes['text'] = text
			r.origMathSource = math.source
			math.parentNode.replaceChild( r, math )
		else:
			# Not empty, not a name. Let's consider it a "number"
			try:
				float(text) # ensure it is a number
			except ValueError:
				# not a number. Oh well.
				continue
			r = document.createElement( 'mathnumber' )
			r.attributes['text'] = text
			r.origMathSource = math.source
			math.parentNode.replaceChild( r, math )
