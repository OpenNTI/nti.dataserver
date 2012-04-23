#!/usr/bin/env python2.7

import tempfile


import plasTeX

from plasTeX.TeX import TeX
#from plasTeX.ConfigManager import *
from plasTeX.DOM import Node

import StringIO

import nti.openmath as openmath


def buildDomFromString(docString):
	document = plasTeX.TeXDocument()
	strIO = StringIO.StringIO(docString)
	strIO.name = 'temp'
	tex = TeX(document,strIO)
	document.userdata['jobname'] = 'temp'
	document.userdata['working-dir'] = tempfile.gettempdir()
	tex.parse()
	return document

def simpleLatexDocument(maths):
	doc = r"""\documentclass[12pt]{article} \usepackage{amsmath} \begin{document} """
	mathString = '\n'.join( [str(m) for m in maths] )
	doc = doc + '\n' + mathString + '\n\\end{document}'
	return doc

def mathTexToDOMNodes(maths):
	doc = simpleLatexDocument(maths)
	dom = buildDomFromString(doc)

	return dom.getElementsByTagName('math')

def mathIsEqual(math1, math2):
	return mathChildrenAreEqual(math1.childNodes, math2.childNodes)

def mathChildrenAreEqual(children1, children2):
	math1children = stripEmptyChildren(children1)
	math2children = stripEmptyChildren(children2)

	if len(math1children) != len(math2children):
		return False

	for math1child, math2child in zip(math1children, math2children):
		if not mathChildIsEqual(math1child, math2child):
			return False

	return True

def mathChildIsEqual(child1, child2):
	#If are children aren't even the same type they are probably not equal

	#If they are actually the same thing (only happens in None case I think)
	if child1 == child2:
		return True

	if child1.nodeType != child2.nodeType:
		return False

	if len(child1.childNodes) != len(child2.childNodes):
		return False

	if child1.nodeType == Node.TEXT_NODE:
		text1 = sanitizeTextNodeContent(child1)
		text2 = sanitizeTextNodeContent(child2)

		return type(text1) == type(text2) and text1 == text2

	elif child1.nodeType == Node.ELEMENT_NODE:
		#Simple case we have no children

		if len(child1.arguments) != len(child2.arguments):
			return False
		for arg in child1.arguments:
			arg1 = child1.attributes[arg.name]
			arg2 = child2.attributes[arg.name]
			if not mathChildIsEqual(arg1, arg2):
				return False

		return mathChildrenAreEqual(child1.childNodes, child2.childNodes)


	elif child1.nodeType == Node.DOCUMENT_FRAGMENT_NODE:
		return mathChildrenAreEqual(child1.childNodes, child2.childNodes)

	else:
		#Fallback to string comparison
		return sanitizeTextNodeContent(child1) == sanitizeTextNodeContent(child2)

def stripEmptyChildren(children):
	newChildren = []

	for child in children:
		if child.nodeType == Node.TEXT_NODE:
			text = sanitizeTextNodeContent(child.textContent)

			if len(text) > 0:
				newChildren.append(child)

		else:
			newChildren.append(child)

	return newChildren

def sanitizeTextNodeContent(textNode):
	text = textNode.textContent.strip()
	text = text.replace(',', '')

	return text

import re

naturalNumberPattern = re.compile('^[0-9]+$')
realNumberPattern = re.compile('^[0-9]*\\.[0-9]+$')

def textToType(text):
	try:
		if naturalNumberPattern.match(text):
			return int(text)
	except ValueError:
		pass

	try:
		if realNumberPattern.match(text):
			return float(text)
	except ValueError:
		pass

	return text

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


def grade_one_response(questionResponse, possible_answers):
	"""
	:param questionResponse: The string to evaluate. It may be in latex notation
		or openmath XML notation, or plain text. We may edit the response
		to get something parseable.
	:param list possible_answers: A sequence of possible answers to compare
		`questionResponse` with.
	"""
	answers = mathTexToDOMNodes( possible_answers )
	response = str(questionResponse)
	if not response:
		#The student skipped this question. Always
		#a fail.
		return False

	response_doc = _response_text_to_latex( response )
	response = mathTexToDOMNodes( ( response_doc, ) )

	if len(response) != 1:
		# TODO: How to handle this? We need to present
		# some sort of retry condition?
		raise Exception( u"Invalid response format '%s' (%s/%s -> %s/%s)" % (questionResponse, response_doc, type(response_doc), len(response), response) )

	match = False
	for answer in answers:
		for rsp in response:
			match = mathIsEqual( rsp, answer )
			if match:
				return True

	return False

def assess( quiz, responses ):
	result = {}
	for questionId, questionResponse in responses.iteritems():
		result[questionId] = grade_one_response( questionResponse, quiz[questionId].answers )
	return result
