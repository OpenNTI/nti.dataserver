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
		if self.near_sibling(node) is not None:
			output = self.near_sibling(node)
			while len(output.childNodes) > 0:
				output = self.near_child(output)
			return output
		if node.parentNode is None:
			return None
		return self.onestep(node.parentNode)
	def one_word_grab(self,node,offset):
		""" 
		Moves one word forward or back and returns that word
		"""
		if node is None:
			 return '', node, offset
		if node.nodeType != node.TEXT_NODE or offset > len(node.data):
			return self.one_word_grab(self.onestep(node), 0)
		if offset == -1:
			offset = self.beginning(node.data)
		next_space = self.find_space(node.data, offset)
		if next_space >= 0:
			low,high = min(offset,next_space), max(offset,next_space)
			return node.data[low:high], node, next_space
		else:
			new_node = self.onestep(node)
			low = min(offset,self.end(node.data))
			high = max(offset,self.end(node.data))
			return node.data[low:high], new_node, -1
	def n_words(self, node, offset, n):
		wordlist,nd,os = [], node, offset
		for i in range(n):
			new_word, nd, os = self.one_word_grab(nd, os)
			if new_word.strip():
				self.insert(wordlist,new_word.strip())
		return wordlist
	def near_child(self,node): return node.childNodes[self.front_element]
	def remove(self,x): return x.pop(self.front_element)
	def insert(self,x,e): x.insert(self.end(x),e)

class backward(treewalker):
	role = "start"
	front_element = -1
	def beginning(self,a_list): return len(a_list)
	def end(self,a_list): return 0
	def near_sibling(self,node): return node.previousSibling
	def find_space(self,string,offset): return string.rfind(' ',0,offset - 1)
	def context_offset(self,node,lastspace,ctx):
		return len(node.data) - lastspace - len(ctx.contextText)
class forward(treewalker):
	role = "end"
	front_element = 0
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
		# Append additional contexts until 15 characters or 5 contexts
		return_ptr = contentrange.TextDomContentPointer()
		return_ptr.contexts = [return_ctx]
		total_chars = len(left)
		cur_node = directionals.onestep(node)
		# Cycle through successive nodes to get our additional contexts
		while cur_node is not None and total_chars < 15 and len(return_ptr.contexts) < 5:
			while cur_node is not None and \
					cur_node.nodeType != cur_node.TEXT_NODE:
				cur_node = directionals.onestep(cur_node)
			new_context = []
			remainder = cur_node.data.split(' ')
			while total_chars + len(' '.join(new_context)) < 15 and len(remainder) > 0:
				directionals.insert(new_context, directionals.remove(remainder))
			new_ctx_string = ' '.join(new_context).strip()
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

			def seek_text (node, point, start_limit=None):
				if node.nodeType == node.TEXT_NODE:
					back_textnodes = [node.data]
					cur_node = node
					treewalk = {"start":backward(), "end":forward()}[point.role].onestep
					while len(back_textnodes) < len(point.contexts):
						cur_node = treewalk(cur_node)
						if cur_node == None:
							return None 
						if cur_node.nodeType == cur_node.TEXT_NODE:
							back_textnodes.append(cur_node.data)
					for i,cxt in enumerate(point.contexts):
						if back_textnodes[i].find(cxt.contextText)  == -1:
							return None
					pos = node.data.find(point.contexts[0].contextText) + point.edgeOffset
					output = _domrange.position(node,pos)
					# Some checks based on the information that we can gain
					# based on the given start node (start_limit)
					if start_limit is None: return output
					# Check if the ancestor is what it should be
					anc = get_anchorable_ancestor(start_limit.node,node)
					if anc.attributes == None or \
							anc.getAttribute("id") != contentrange.ancestor.elementId:
						return None
					# Is the end we found after the start?
					if output > start_limit: return output
					return None
				else:
					for c in node.childNodes:
						child_result = seek_text(c,point,start_limit)
						if child_result is not None:
							return child_result
				return None

			return_pos = seek_text(ancestor,point,start_limit)
			return return_pos

	output = _domrange.Range()
	point = point_convert(contentrange.start)
	if point.node is None: return None
	output.start.set(point.node,point.offset)
	point = point_convert(contentrange.end,point)
	if point is None: return None
	output.end.set(point.node,point.offset)
	return output
