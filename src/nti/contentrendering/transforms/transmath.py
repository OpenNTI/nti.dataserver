#!/usr/bin/env python
# $Id$
# Disable pylint warning about "too many methods" on the Command subclasses,
# and "deprecated string" module
#pylint: disable=R0904,W0402
from plasTeX import Node
import plasTeX.Base
import string

import logging
logger = logging.getLogger(__name__)

from zope import interface
from . import interfaces
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
	for name in ['nst', 'nnd', 'nrd', 'nth']:
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
		try:

			text = math.textContent

			#Remove any empty math nodes from the dom.	There are likely none
			#Note the addition of the childNode check its is not enough to just
			#check if the textContent is none
			if not(text):
				#Found empty mathnode remove it from the parent
				logger.info( 'Found empty math node' )
				math.parentNode.removeChild(math)
			elif all( [c in string.ascii_letters for c in text] ):
				r = None
				#print "Found math node %s to mathname" % math.toXML()
			##	if math.previousSibling:
			##		prevText = (math.previousSibling.textContent or '').rstrip()
			##		if prevText.lower().endswith( ' angle' ):
			##			r = document.createElement( 'mathangle' )
			##		elif prevText.lower().endswith( ' line') or prevText == 'Line':
			##			r = document.createElement( 'mathline' )
			##	if r is None:
			##		r = document.createElement( 'mathname' )
				r = document.createElement( 'mathname' )
				r.attributes['text'] = text
				r.origMathSource = math.source
				math.parentNode.replaceChild( r, math )
			else:
				#at this point we better have a a number
				#print 'Replacing mathnumber'
				float(text)
				r = document.createElement( 'mathnumber' )
				r.attributes['text'] = text
				r.origMathSource = math.source
				math.parentNode.replaceChild( r, math )

		except ValueError:
			pass
		except Exception:
			logger.exception( 'Unable to replace %s parents children are %s', math, [x for x in enumerate(math.parentNode)] )

