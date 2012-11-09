from __future__ import print_function, unicode_literals

import six

from zopyx.txng3.core import parsetree as zopyx_parsetree

import logging
logger = logging.getLogger( __name__ )

class _NodeProxy(object):
	def __init__(self, v):
		self.v = v
	
	def getValue(self):
		return self.v
	
def node_splitter(node, splitter):
	if isinstance(node, six.string_types):
		return zopyx_parsetree.node_splitter(_NodeProxy(node), splitter)
	else:
		return zopyx_parsetree.node_splitter(node, splitter)
	