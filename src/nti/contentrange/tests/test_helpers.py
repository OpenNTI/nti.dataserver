#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
$Id$
"""

from __future__ import print_function, unicode_literals
import xml.dom
import xml.dom.minidom
import hamcrest
import sys
from hamcrest import assert_that, is_, none
from hamcrest.core.base_matcher import BaseMatcher
from nti.contentrange import _domrange, _convertrange

def range_comparison_check(r1,r2,how,desired):
	assert_that( r1.compareBoundaryPoints(how,r2), is_(desired) )
def point_in_range_check(r,node,offset,desired):
	assert_that( r.pointInside(node,offset), is_(desired) )

def range_conversion_check(r,solution):
	if hasattr(r,'__iter__') and hasattr(solution,'__iter__'):
		return [range_conversion_check(x,sln) for x,sln in zip(r,solution)]
	cr = _convertrange.domToContentRange(r)
	if solution is not None:
		assert_that( cr, is_( context_check(*solution) ) )
	return cr

def round_trip_check(r,newdoc=None,solution=None):
	NO_CHECK = 0
	if hasattr(r,'__iter__'):
		if hasattr(solution,'__iter__'):
			return zip(*[round_trip_check(x,newdoc,sln) for x,sln in zip(r,solution)])
		return zip(*[round_trip_check(x,newdoc) for x in r])
	cr = _convertrange.domToContentRange(r)
	if newdoc is None:
		bk = _convertrange.contentToDomRange(cr,r.get_root())
		if solution is None: assert_that ( str(bk), is_( str(r) ) )
	else:
		if hasattr(newdoc,'nodeType') == False: newdoc = newdoc.root
		bk = _convertrange.contentToDomRange(cr,newdoc)
	if solution is not None and solution != NO_CHECK:
		assert_that ( str(bk), is_( solution ) )
	return cr, bk

class Document(object):
	def __init__(self,string,strip=True):
		if strip: string = string.replace('\n','').replace('\t','')
		self.document = xml.dom.minidom.parseString(string)
		self.root = self.document.documentElement
		self.focus = self.root

	def text_hunt(self,text,node=None,offset=False,querypos=0):
		if node is None: node = self.focus
		out = TextHunter(node,text).hunt()
		if offset == False: return out
		return out, out.data.find(text) + querypos + ((len(text)+1) if querypos < 0 else 0)

	def element_hunt(self,attr,value,node=None):
		if node is None: node = self.focus
		return ElementHunter(node,attr,value).hunt()

	def downpath(self, path=[], ancestor=None):
		if ancestor is None: ancestor = self.focus
		if len(path) == 0:
			return ancestor
		else:
			return self.downpath(path[1:],ancestor.childNodes[path[0]])

class Hunter(object):
	def __init__(self, node):
		self.root = node
	def hunt(self, node=None):
		if node is None: node = self.root
		if self.confirm(node): return node
		for c in node.childNodes:
			child_result = self.hunt(c)
			if child_result is not None: return child_result
		return None

class TextHunter(Hunter):
	def __init__(self, node, text):
		self.root, self.text = node, text
	def confirm(self, node):
		return node.nodeType == node.TEXT_NODE and node.data.find(self.text) >= 0

class ElementHunter(Hunter):
	def __init__(self, node, attribute, value):
		self.root, self.attr, self.value = node, attribute, value
	def confirm(self, node):
		return node.nodeType == node.ELEMENT_NODE and \
				node.getAttribute(self.attr) == self.value

class ContextChecker(BaseMatcher):
	def __init__ (self, *args):
		self.vals = args
	def _matches (self, other):
		vals = []
		for pt in [other.start, other.end, other.ancestor]:
			if hasattr(pt,'contexts'):
				vals.extend([pt.contexts[0].contextText,pt.contexts[0].contextOffset])
			else: vals.extend([pt.elementId,pt.elementTagName])
		self.result = 'Wanted: ' + str(self.vals) + '\nGot: ' + str(vals)
		for x,y in zip(self.vals, vals):
			if x is not None and x != y: return False
		return True
	def describe_to (self, description):
		description.append_text('\n\n' + self.result + '\n')
def context_check(st=None, so=None, ft=None, fo=None, anc_id=None, anc_tag=None):
	return ContextChecker(st, so, ft, fo, anc_id, anc_tag)


