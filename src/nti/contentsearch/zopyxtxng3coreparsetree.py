from __future__ import print_function, unicode_literals

###########################################################################
# TextIndexNG V 3                
# The next generation TextIndex for Zope
#
# This software is governed by a license. See
# LICENSE.txt for the terms of this license.
###########################################################################

import six

from zopyx.txng3.core.parsetree import BaseNode, WordNode, AndNode

import logging
logger = logging.getLogger( __name__ )

def node_splitter(node, splitter):
	"""Split word nodes with splitter."""
	
	if isinstance(node, six.string_types):
		node = WordNode(node)
		
	v = node.getValue()
	if isinstance(v, (list, tuple)):
		for child in v:
			node_splitter(child, splitter)
	elif isinstance(v, BaseNode):
		node_splitter(v, splitter)
	elif isinstance(v, unicode):
		split = splitter.split(v)
		if len(split) == 1:
			node.setValue(split[0])
		elif len(split) > 1:
			original_node = node
			nodes = [WordNode(v) for v in split]
			node = AndNode(nodes)
			if original_node._parent:
				parent_value = original_node._parent.getValue()
				if isinstance(parent_value, BaseNode):
					parent_value = node
				elif isinstance(parent_value, (tuple, list)):
					parent_value = list(parent_value)
					parent_value[parent_value.index(original_node)] = node
				original_node._parent.setValue(parent_value)
	return node
