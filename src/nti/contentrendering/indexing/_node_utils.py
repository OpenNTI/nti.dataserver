# -*- coding: utf-8 -*-
"""
Indexing mindom utilities.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from xml.dom.minidom import Node

def get_ntiid(node):
	"""
	return ntiid attribute value for the specified node
	"""
	attrs = node.attributes if node is not None else None
	return attrs['ntiid'].value if attrs and attrs.has_key('ntiid') else None

def _add_ntiid_to_set(pset, node):
	ntiid = get_ntiid(node)
	if ntiid:
		pset.add(unicode(ntiid))
	return pset

def get_related(node):
	"""
	return a list with the related nttids for this node
	"""
	related = set()
	for child in getattr(node,'childNodes',()):
		if child.nodeType == Node.ELEMENT_NODE:
			if child.localName == 'topic':
				_add_ntiid_to_set(related, child)
			elif child.localName == 'Related':
				for c in child.childNodes:
					if c.nodeType == Node.ELEMENT_NODE and c.localName == 'page':
						_add_ntiid_to_set(related, c)

	result = sorted(related)
	return result

def get_text(node):
	"""
	return the text part of the specified node
	"""
	txt = node.text
	txt = unicode(txt.strip()) if txt else u''
	return txt

def get_tail(node):
	"""
	return the tail part of the specified node
	"""
	txt = node.tail
	txt = unicode(txt.strip()) if txt else u''
	return txt

def get_node_content(node):
	"""
	return the text and tail parts (space separated) of the specified node
	"""
	result = (get_text(node), get_tail(node))
	result = ' '.join(result)
	return result.strip()

def get_attribute(node, name):
	"""
	return the value for the specified attribute name from the specified node
	"""
	attributes = node.attrib if node is not None else {}
	return attributes.get(name, None)
