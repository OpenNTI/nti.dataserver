#!/usr/bin/env python
"""
Support functions for comparing latex Math DOMs using PlasTeX
"""
from __future__ import print_function, unicode_literals
import logging
logger = logging.getLogger(__name__)

from sympy.parsing.sympy_parser import parse_expr, TokenError

from nti.assessment import interfaces
from zope import interface
from zope import component
from zope.component.interfaces import ComponentLookupError

def _mathIsEqual(math1, math2):
	if math1 is None or math2 is None:
		# We follow the rules for NULL: it's not equal to anything,
		# even itself
		return False
	return _mathChildrenAreEqual(math1.childNodes, math2.childNodes) or \
		(_all_text_children(math1) and _all_text_children(math2) and _text_content_equal(math1, math2))

def _mathChildrenAreEqual(children1, children2):
	math1children = _stripEmptyChildren(children1)
	math2children = _stripEmptyChildren(children2)

	if len(math1children) != len(math2children):
		return False

	for math1child, math2child in zip(math1children, math2children):
		if not _mathChildIsEqual(math1child, math2child):
			return False

	return True

def _importantChildNodes( childNodes ):
	"""
	Given the child nodes of a node, return a fresh list of those
	that are important for comparison purposes. Spaces are not considered important
	"""
	return [x for x in childNodes if x.nodeType != x.TEXT_NODE or x.textContent.strip()]

def _all_text_children( childNode ):
	return all( (x.nodeType == x.TEXT_NODE for x in childNode.childNodes) )

def _text_content_equal( child1, child2 ):
	"""
	Checks to see if the two nodes have equivalent text. If they compare
	equal from a purely textual standpoint, then that is the answer. Otherwise,
	we try to compare them from a symbolic version of their text.
	"""
	return _sanitizeTextNodeContent(child1) == _sanitizeTextNodeContent(child2) or \
		_symbolic( child1 ) == _symbolic( child2 )

def _symbolic( child ):
	"""
	Returns a symbolic version of the child, if possible. Always
	returns something that will be valid for an equality test
	with other objects given to this method (i.e., should not return None).
	"""
	try:
		return parse_expr( child.textContent )
	except (TokenError,SyntaxError,AttributeError):
		return child

def _mathChildIsEqual(child1, child2):
	#If are children aren't even the same type they are probably not equal

	#If they are actually the same thing (only happens in None case I think)
	if child1 == child2:
		return True

	if child1.nodeType != child2.nodeType or len(_importantChildNodes(child1.childNodes)) != len(_importantChildNodes(child2.childNodes)):
		return False

	if child1.nodeType == child1.TEXT_NODE:
		text1 = _sanitizeTextNodeContent(child1)
		text2 = _sanitizeTextNodeContent(child2)

		return type(text1) == type(text2) and text1 == text2

	if child1.nodeType == child1.ELEMENT_NODE:
		# Check that the arguments and the children are equal
		return len(child1.arguments) == len(child2.arguments) and \
		  all( (_mathChildIsEqual(child1.attributes[k.name],child2.attributes[k.name]) for k in child1.arguments) ) and \
		  ((_all_text_children(child1) and _all_text_children(child2) and _text_content_equal(child1, child2)) or
		   _mathChildrenAreEqual(child1.childNodes, child2.childNodes))


	if child1.nodeType == child1.DOCUMENT_FRAGMENT_NODE:
		return _mathChildrenAreEqual(child1.childNodes, child2.childNodes)

	#Fallback to string comparison
	return _sanitizeTextNodeContent(child1) == _sanitizeTextNodeContent(child2)

_stripEmptyChildren = _importantChildNodes

def _sanitizeTextNodeContent(textNode):
	text = textNode.textContent.strip()
	text = text.replace(',', '')
	# Whitespace is insignificant
	text = text.replace( ' ', '' )

	return text


def grade( solution, response ):
	try:
		converter = component.getMultiAdapter( (solution,response), interfaces.IResponseToSymbolicMathConverter )
	except ComponentLookupError:
		logger.warning( "Unable to grade math, assuming wrong", exc_info=True )
		return False

	solution_dom = converter.convert( solution )
	response_dom = converter.convert( response )

	return _mathIsEqual( solution_dom, response_dom )

@interface.implementer( interfaces.IQSymbolicMathGrader )
class Grader(object):

	def __init__( self, part, solution, response ):
		self.solution = solution
		self.response = response

	def __call__( self ):
		result = grade( self.solution, self.response )
		if not result and not self.response.value.startswith( '<' ):
			#Hmm. Is there some trailing text we should brush away from the response?
			# Only try if it's not OpenMath XML (which only comes up in test cases now)
			parts = self.response.value.rsplit( ' ', 1 )
			if len( parts ) == 2:
				response = type(self.response)( parts[0] )
				result = grade( self.solution, response )
				if result:
					self.response = response
		return result
