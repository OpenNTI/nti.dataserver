#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
search internalization

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.datastructures import InterfaceObjectIO

from . import interfaces as search_interfaces

@interface.implementer(ext_interfaces.IInternalObjectUpdater)
@component.adapter(search_interfaces.ISearchQuery)
class _QueryObjectUpdater(object):

	__slots__ = ('obj',)

	def __init__(self, obj):
		self.obj = obj

	def updateFromExternalObject(self, externalObject, *args, **kwargs ):
		for name in ('IsEmtpty', 'IsBatching', 'IsPrefixSearch', 'IsPhraseSearch',
					'IsDescendingSortOrder'):
			if name in externalObject:
				del externalObject[name]

		result = InterfaceObjectIO(self.obj, search_interfaces.ISearchQuery).updateFromExternalObject(externalObject)
		return result
