# -*- coding: utf-8 -*-
"""
Book indexing interfaces

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from nti.contentrendering import interfaces as cr_interfaces

class IWhooshBookIndexer(cr_interfaces.IBookIndexer):
	
	def process_topic(node, writer):
		"""
		Index the specified book topic
		
		:param node: The :class:`IEclipseMiniDomTopic`.
		:param writer: Whoosh indexwriter
		"""
		
	def process_book(book, writer):
		"""
		Index the specified book 
		
		:param book: The :class:`IRenderedBook`.
		:param writer: Whoosh indexwriter
		"""

	def index(book, indexdir=None, indexname=None):
		"""
		Index the specified book 
		
		:param book: The :class:`IRenderedBook`.
		:param indexdir: Output directory
		:param indexname: Index name
		"""