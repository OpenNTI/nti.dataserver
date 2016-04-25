#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.container.contained import Contained

from zope.traversing.interfaces import IPathAdapter

from ZODB.interfaces import IConnection

from nti.contentfolder.model import RootFolder

@interface.implementer(IPathAdapter)
class _OFSPathAdapter(Contained):
	"""
	XXX: Adapter to be used only in unit tests.
	"""

	__name__ = "ofs"

	def __init__(self, context, request):
		self.context = context
		self.request = request
		self.__parent__ = context

	def __getitem__(self, key):
		if key == 'root':
			try:
				result = self.context._ofs_root
			except AttributeError:
				result = self.context._ofs_root = RootFolder()
				result.__parent__ = self.context
				IConnection(self.context).add(result)
			return result
		raise KeyError(key)

