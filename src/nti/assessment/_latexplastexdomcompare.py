#!/usr/bin/env python
"""
Support functions for comparing latex Math DOMs using PlasTeX
"""
from __future__ import print_function, unicode_literals
import sys

from nti.assessment import interfaces
from zope import component


def _mathIsEqual(math1, math2):
	return _mathChildrenAreEqual(math1.childNodes, math2.childNodes)

def _mathChildrenAreEqual(children1, children2):
	math1children = _stripEmptyChildren(children1)
	math2children = _stripEmptyChildren(children2)

	if len(math1children) != len(math2children):
		return False

	for math1child, math2child in zip(math1children, math2children):
		if not _mathChildIsEqual(math1child, math2child):
			return False

	return True

def _mathChildIsEqual(child1, child2):
	#If are children aren't even the same type they are probably not equal

	#If they are actually the same thing (only happens in None case I think)
	if child1 == child2:
		return True

	if child1.nodeType != child2.nodeType:
		return False

	if len(child1.childNodes) != len(child2.childNodes):
		return False

	if child1.nodeType == child1.TEXT_NODE:
		text1 = _sanitizeTextNodeContent(child1)
		text2 = _sanitizeTextNodeContent(child2)

		return type(text1) == type(text2) and text1 == text2

	elif child1.nodeType == child1.ELEMENT_NODE:
		#Simple case we have no children

		if len(child1.arguments) != len(child2.arguments):
			return False
		for arg in child1.arguments:
			arg1 = child1.attributes[arg.name]
			arg2 = child2.attributes[arg.name]
			if not _mathChildIsEqual(arg1, arg2):
				return False

		return _mathChildrenAreEqual(child1.childNodes, child2.childNodes)


	elif child1.nodeType == child1.DOCUMENT_FRAGMENT_NODE:
		return _mathChildrenAreEqual(child1.childNodes, child2.childNodes)

	else:
		#Fallback to string comparison
		return _sanitizeTextNodeContent(child1) == _sanitizeTextNodeContent(child2)

def _stripEmptyChildren(children):
	newChildren = []

	for child in children:
		if child.nodeType == child.TEXT_NODE:
			text = _sanitizeTextNodeContent(child.textContent)

			if len(text) > 0:
				newChildren.append(child)

		else:
			newChildren.append(child)

	return newChildren

def _sanitizeTextNodeContent(textNode):
	text = textNode.textContent.strip()
	text = text.replace(',', '')

	return text


def grade( solution, response ):
	converter = component.getMultiAdapter( (solution,response), interfaces.IResponseToSymbolicMathConverter )
	# TODO: Caching these DOMs based on string values. Parsing them is expensive.
	solution_dom = converter.convert( solution )
	response_dom = converter.convert( response )

	return _mathIsEqual( solution_dom, response_dom )

def factory( solution, response ):
	return sys.modules[__name__]

component.moduleProvides(interfaces.IQSymbolicMathGrader)
