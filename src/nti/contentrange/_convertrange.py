#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
$Id$
"""

from __future__ import print_function, unicode_literals
import xml.dom
import xml.dom.minidom
import sys
import contentrange
import _domrange
import re
import math
import time

class treewalker(object):
	"""
	Collection of methods for navigating back and forth in a linear fashion
	through DOM trees
	"""
	def onestep(self,node):
		""" 
		Goes to next or previous node in the order that nodes come in the XML
		representation of the tree
		"""
		cur_node = node
		while cur_node is not None and self.near_sibling(cur_node) is None:
			cur_node = cur_node.parentNode
		if cur_node is None: return None
		cur_node = self.near_sibling(cur_node)
		while len(cur_node.childNodes) > 0:
			cur_node = self.near_child(cur_node)
		return cur_node
		if self.near_sibling(node) is not None:
			output = self.near_sibling(node)
			while len(output.childNodes) > 0:
				output = self.near_child(output)
			return output
		if node.parentNode is None:
			return None
		return self.onestep(node.parentNode)
	def first_word(self,node):
		if node is None or node.nodeType != node.TEXT_NODE:
			 return '', node, offset
		return re.search(self.first_word_regexp,node.data).group(0)
	def near_child(self,node): return node.childNodes[self.front_element]
	def remove(self,x): return x.pop(self.front_element)
	def insert(self,x,e): x.insert(self.end(x),e)

class backward(treewalker):
	role = "start"
	front_element = -1
	first_word_regexp = '\S*\s?$'
	def beginning(self,a_list): return len(a_list)
	def end(self,a_list): return 0
	def near_sibling(self,node): return node.previousSibling
	def find_space(self,string,offset): return string.rfind(' ',0,offset - 1)
	def context_offset(self,node,lastspace,ctx): return len(node.data) - lastspace
class forward(treewalker):
	role = "end"
	front_element = 0
	first_word_regexp = '^\s?\S*'
	def beginning(self,a_list): return 0
	def end(self,a_list): return len(a_list)
	def near_sibling(self,node): return node.nextSibling
	def find_space(self,string,offset): return string.find(' ',offset + 1)
	def context_offset(self,node,lastspace,ctx): return lastspace

def is_anchorable (node):
	if node is None:
		return False
	if node.nodeType == node.TEXT_NODE:
		cur_node = node.parentNode
		while cur_node is not None:
			if is_anchorable(cur_node):
				return True
			cur_node = cur_node.parentNode
		return False
	if node.nodeType == node.ELEMENT_NODE:
		if node.getAttribute('id') == '' or node.tagName == '':
			return False
		if node.getAttribute('data-non-anchorable') == 'true':
			return False
		illegal_starts = ('MathJax','ext-gen') # ext-gen controversial at the moment
		for x in illegal_starts:
			if node.getAttribute('id').startswith(x): return False
		return True
	return False

def list_all_children (node):
	if len(node.childNodes) == 0: return [node]
	total = []
	for c in node.childNodes: total.extend(list_all_children(c))
	return total

def get_anchorable_ancestor(a,b=None):
	if b is not None:
		output = _domrange.find_common_ancestor(a,b)
	else:
		output = a
	while is_anchorable(output) == False or output.nodeType == output.TEXT_NODE:
		output = output.parentNode
		if output is None: return None
	return output

def domToContentRange(domrange):

	""" Converts a DOM range to a content range """
	def convert(node,offset, directionals):
		if node.nodeType == node.TEXT_NODE: 
			return point_convert(node, offset, directionals)
		else:	
			return element_convert(node)

	def element_convert(element):
		""" Converts a pointer to a DOM element to its contentrange equivalent """
		return_ptr = contentrange.ElementDomContentPointer()
		return_ptr.elementId = element.getAttribute('id')
		return_ptr.elementTagName = element.tagName
		return return_ptr

	def point_convert(node,offset,directionals):
		""" Converts a specific point in text to its contentrange equivalent """
		# Generate the primary text context
		return_ctx = contentrange.TextContext()
		left = node.data[:offset]
		right = node.data[offset:]
		lastspace = left[:-1].rfind(' ') + 1
		nextspace = right[1:].find(' ') + 1
		if nextspace == 0: nextspace = len(node.data)
		left = left[lastspace:]
		right = right[:nextspace]
		return_ctx.contextText = left+right
		return_ctx.contextOffset = \
				 directionals.context_offset(node,lastspace,return_ctx)
		# Append additional contexts until 15 characters or 5 secondary contexts
		return_ptr = contentrange.TextDomContentPointer()
		return_ptr.contexts = [return_ctx]
		total_chars = 0
		cur_node = directionals.onestep(node)
		# Cycle through successive nodes to get our additional contexts
		while cur_node is not None and total_chars < 15 and len(return_ptr.contexts) <= 5:
			if cur_node is None: break
		 	if cur_node.nodeType != cur_node.TEXT_NODE:
				new_ctx_string = ''
			else:
				new_ctx_string = directionals.first_word(cur_node)
			new_ctx = contentrange.TextContext()
			new_ctx.contextText = new_ctx_string
			total_chars += len(new_ctx_string)
			new_ctx.contextOffset = len(new_ctx_string)
			return_ptr.contexts.append(new_ctx)
			cur_node = directionals.onestep(cur_node)
		return_ancestor = get_anchorable_ancestor(node.parentNode)
		return_ptr.ancestor = element_convert(return_ancestor)
		return_ptr.edgeOffset = offset - lastspace
		return_ptr.role = directionals.role
		return return_ptr

	start_ptr = convert(domrange.start.node,domrange.start.offset,backward())
	end_ptr = convert(domrange.end.node,domrange.end.offset,forward())
	output = contentrange.DomContentRangeDescription()
	output.start = start_ptr;
	output.end = end_ptr;
	ancestor_to_convert = get_anchorable_ancestor(domrange.ancestor)
	output.ancestor = element_convert(ancestor_to_convert)
	return output

def contentToDomRange(contentrange,document):
	def seek_dom_element (ancestor,ptr):
		if ancestor.nodeType == ancestor.ELEMENT_NODE and \
				ancestor.getAttribute('id') == ptr.elementId and \
				ancestor.tagName == ptr.elementTagName:
			return ancestor
		else:
			for c in ancestor.childNodes:
				if seek_dom_element(c,ptr) is not None: return c
		return None

	def point_convert(point, start_limit=None):
		if hasattr(point,'elementId') and hasattr(point,'elementTagName'):
			# Element pointer case
			return _domrange.position(seek_dom_element(document,point),0)
		else:
			# Text pointer case
			ancestor = seek_dom_element(document,contentrange.ancestor)
			treewalk = {"start":backward(), "end":forward()}[point.role].onestep

			def get_matches (node, point, start_limit=None):
				if node.nodeType == node.TEXT_NODE:
					# Get all matches for the primary context
					allmatches, left = [], -1
					while 1:
						left = node.data.find(point.contexts[0].contextText,left+1)
						if left == -1: break
						f = math.sqrt(len(node.data)) * 2 + 1.0
						if point.role == "start":
							offset = len(node.data) - point.contexts[0].contextOffset
						else:
							offset = point.contexts[0].contextOffset
						score = f / (f + abs(left - offset))
						allmatches.append((left,score))
					# Check additional contexts
					score_multiplier = 1
					cur_node = node
					failed = False
					for i,cxt in enumerate(point.contexts[1:]):
						cur_node = treewalk(cur_node)
						if cur_node is None: failed = True
						elif cur_node.nodeType == cur_node.TEXT_NODE and \
								cur_node.data.find(cxt.contextText) == -1: failed = True
						elif cur_node.nodeType == cur_node.ELEMENT_NODE and \
								cxt.contextText != '': failed = True
						if failed:
							# Differs from the spec's i/i+0.5 formula because i
							# is the index only among _secondary_ contexts
							score_multiplier = (i + 1) / (i + 1.5)
							break
					cur_node = treewalk(cur_node)
					nsc = len(point.contexts) - 1
					totalchars = sum([len(c.contextText) for c in point.contexts[1:]])
					if score_multiplier == 1 and nsc < 5 and totalchars < 15:
						if cur_node is not None:
							score_multiplier = (nsc + 1) / (nsc + 1.5)
					outputs = [(_domrange.position(node,o[0] + point.edgeOffset),o[1] * score_multiplier)
									 for o in allmatches]
					if start_limit is None: return outputs
					return filter(lambda x: x[0] > start_limit, outputs)
				else:
					child_results = []
					sl = start_limit
					if start_limit is not None:
						if _domrange.position(node,999999) < start_limit:
							return []
						elif _domrange.position(node,0) > start_limit:
							sl = None
					for c in node.childNodes:
						a = get_matches(c,point,sl)
						if a is not None: child_results.extend(a)
					return child_results
				return []

			all_matches = sorted(get_matches(ancestor,point,start_limit),key=lambda x:x[1])
			#print ("All: ",all_matches)
			#print ("Contexts: ",[c.contextText+'/'+str(c.contextOffset) for c in point.contexts])
			return all_matches[-1][0] if len(all_matches) > 0 else None


	output = _domrange.Range()
	point = point_convert(contentrange.start)
	if point is None or point.node is None: return None
	output.start.set(point.node,point.offset)
	point = point_convert(contentrange.end,point)
	if point is None: return None
	output.end.set(point.node,point.offset)
	return output
