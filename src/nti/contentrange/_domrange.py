#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
$Id$
"""

import xml.dom
import sys

class position(object):
	node, offset = None, 0
	def __init__(self,node=None,offset=None,parent=None):
		self.parent = parent
		if node is not None and offset is not None: self.set(node,offset)

	def updating(f):
		# Call parent range's update function after setting start or end nodes
		def inner_func(*args, **kwargs):
			f(*args, **kwargs)
			if args[0].parent is not None: args[0].parent.update()
		return inner_func

	@updating
	def set(self, node, offset):
		self.node, self.offset = node,offset
		if node is not None and node.nodeType == node.TEXT_NODE and \
					self.offset > len(node.data):
			self.offset = len(node.data)

	@updating
	def set_before(self,node):
		self.node, self.offset = node.parentNode, childIndex(node)

	@updating
	def set_after(self,node):
		self.node, self.offset = node.parentNode, childIndex(node) + 1

	def __cmp__(self, other):
		if self.node == other.node: 
			return (self.offset).__cmp__(other.offset)
		self_index, other_index = -1,-1
		ancestor = find_common_ancestor(self.node,other.node)
		if ancestor is None:
			return None
		for i,c in enumerate(ancestor.childNodes):
			if is_ancestor(c,self.node): self_index = i
			if is_ancestor(c,other.node): other_index = i
		if is_ancestor(self.node,other.node):
			if other_index < self.offset: return 1
			return -1
		if is_ancestor(other.node,self.node):
			if self_index < other.offset: return -1
			return 1
		if other_index < self_index: return 1
		return -1

class Range(object):

	ancestor = None
	collapsed = False;
	START_TO_START = 0
	START_TO_END = 1
	END_TO_START = 2
	END_TO_END = 3

	def __init__(self, sn=None, so=None, fn=None, fo=None):
		self.start = position(parent=self)
		self.end = position(parent=self)
		if sn is not None and so is not None: self.set_start(sn,so)
		if fn is not None and fo is not None: self.set_end(fn,fo)

	def update(self):
		if self.start.node is not None and self.end.node is not None:
			self.ancestor = find_common_ancestor(self.start.node,self.end.node)
		self.collapsed = self.end .__cmp__(self.start) in (0, -1)

	def pointInside(self, node, offset):
		p = position(node,offset)
		return self.start <= p and self.end >= p

	def compareBoundaryPoints(self, how, other):
		if how == self.START_TO_START:
			return (self.start).__cmp__(other.start)
		if how == self.START_TO_END:
			return (self.start).__cmp__(other.end)
		if how == self.END_TO_START:
			return (self.end).__cmp__(other.start)
		if how == self.END_TO_END:
			return (self.end).__cmp__(other.end)

	def set_start(self,node,offset): self.start.set(node,offset)
	def set_end(self,node,offset): self.end.set(node,offset)
	def set_start_before(self,node): self.start.set_before(node)
	def set_start_after(self,node): self.start.set_after(node)
	def set_end_before(self,node): self.end.set_before(node)
	def set_end_after(self,node): self.end.set_after(node)

	def get_root(self): return get_root(self.ancestor)

	def collapse(self,to_start):
		if to_start:
			self.end.set(self.start.node, self.start.offset)
		else:
			self.start.set(self.end.node, self.end.offset)

	# Mainly for debugging purposes
	"""def path_from_root(self,node):
		cn = node
		result = []
		while cn.parentNode is not None:
			result = [childIndex(cn)] + result
			cn = cn.parentNode
		return result"""

	# Returns a string of all text between start and end in the order that it
	# would appear in the XML DOM representation
	def stringify(self):
		if self.collapsed:
			return ""
		if self.ancestor is None: raise Exception("No common ancestor found")
		cur_node,cur_offset = self.start.node, self.start.offset
		result = []
		while True:
			if cur_node.nodeType == cur_node.TEXT_NODE:
				if cur_node == self.end.node:
					result.append(cur_node.data[cur_offset:self.end.offset])
					break
				else:
					result.append(cur_node.data[cur_offset:])
					cur_offset = childIndex(cur_node) + 1
					cur_node = cur_node.parentNode
			else:
				if cur_node == self.end.node and cur_offset == self.end.offset:
					break
				if cur_offset < len(cur_node.childNodes):
					cur_node = cur_node.childNodes[cur_offset]
					cur_offset = 0
				else:
					cur_offset = childIndex(cur_node) + 1
					cur_node = cur_node.parentNode
		return ''.join(result)

	__str__ = stringify

def is_ancestor(ancestor,descendant):
	if ancestor == descendant: 
		return True
	if ancestor == None or descendant == None:
		return False
	return is_ancestor(ancestor,descendant.parentNode)

def find_common_ancestor(a,b):
	ancestor = a
	while ancestor is not None and is_ancestor(ancestor,b) == False:
		ancestor = ancestor.parentNode
	return ancestor

def childIndex(node):
	children = node.parentNode.childNodes
	for i,c in enumerate(children):
		if c == node:
			return i

def get_root(node):
	if node.parentNode is None or node.parentNode.nodeType == node.DOCUMENT_NODE: return node
	return get_root(node.parentNode)
