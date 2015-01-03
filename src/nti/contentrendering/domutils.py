#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

def findNodes(node, nodeName):
	nodes = []
	
	if getattr(node, 'nodeName', '') == nodeName:
		nodes.append(node)

	if getattr(node, 'attributes', None):
		for attrval in node.attributes.values():
			if getattr(attrval, 'childNodes', None):
				for child in attrval.childNodes:
					nodes.extend(findNodes(child, nodeName))

	if node.childNodes:
		for child in node.childNodes:
			nodes.extend(findNodes(child, nodeName))

	return list(set(nodes))

def findNodesStartsWith(node, startsWith):
	nodes = []
	
	if getattr(node, 'nodeName', '').startswith(startsWith):
		nodes.append(node)

	if getattr(node, 'attributes', None):
		for attrval in node.attributes.values():
			if getattr(attrval, 'childNodes', None):
				for child in attrval.childNodes:
					nodes.extend(findNodesStartsWith(child, startsWith))

	if node.childNodes:
		for child in node.childNodes:
			nodes.extend(findNodesStartsWith(child, startsWith))

	return list(set(nodes))

def get_or_create_node_in_document_beneath_with_name(parent, nodeName):
	"""
	 Return an existing or newly added node directly a child of `parent.`
	:param parent: The node in the document to be the parent of the node.
	:param str nodeName: A string naming the new node.
	"""
	node = parent.getElementsByTagName(nodeName)

	if len(node) > 0:
		node = node[0]
	else:
		node = parent.ownerDocument.createElement(nodeName)
		parent.appendChild(node)
	return node
getOrCreateNodeInDocumentBeneathWithName=get_or_create_node_in_document_beneath_with_name

def node_has_attribute_with_value(node, attrname, attrval):
	"""
	:return: True if the `node` has an attribute whose value is `attrval`.
	"""
	try:
		if not node.hasAttribute(attrname):
			return False
		# getAttribute returns '' for non-existant attrs
		return node.getAttribute(attrname) == attrval
	except AttributeError:
		return False
