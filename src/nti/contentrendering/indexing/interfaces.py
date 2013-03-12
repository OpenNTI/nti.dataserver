# -*- coding: utf-8 -*-
"""
Book indexing interfaces

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from nti.contentrendering import interfaces as cr_interfaces

class IWhooshBookIndexer(cr_interfaces.IBookIndexer):
	
	def process_topic(node, writer, language):
		"""
		Index the specified book topic
		
		:param node: The :class:`IEclipseMiniDomTopic`.
		:param writer: Whoosh indexwriter
		:param language: Node text language
		"""
		
	def process_book(book, writer, language):
		"""
		Index the specified book 
		
		:param book: The :class:`IRenderedBook`.
		:param writer: Whoosh indexwriter
		:param language: Book text language
		"""

	def index(book, indexdir=None, indexname=None):
		"""
		Index the specified book 
		
		:param book: The :class:`IRenderedBook`.
		:param indexdir: Output directory
		:param indexname: Index name
		"""
