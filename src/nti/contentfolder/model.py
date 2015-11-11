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

from nti.common.property import alias

from nti.containers.containers import CaseInsensitiveCheckingLastModifiedBTreeContainer

from nti.schema.fieldproperty import createDirectFieldProperties

from .interfaces import IRootFolder
from .interfaces import IContentFolder

@interface.implementer(IContentFolder)
class ContentFolder(CaseInsensitiveCheckingLastModifiedBTreeContainer,
					Contained):
	__external_can_create__ = False
	createDirectFieldProperties(IContentFolder)

	name = alias('__name__')

	def __init__(self, *args, **kwargs):
		super(ContentFolder, self).__init__()
		self.name = kwargs.get('name')
		self.use_blobs = kwargs.get('use_blobs', True)
		self.title = kwargs.get('title') or self.name
		self.description = kwargs.get('description') or self.title
		
	def append(self, obj):
		name = obj.name
		if name in self:
			del self[name]
		self[name] = obj

@interface.implementer(IRootFolder)
class RootFolder(ContentFolder):
	createDirectFieldProperties(IRootFolder)

	def __init__(self, *args, **kwargs):
		kwargs['name'] = kwargs.get('name') or 'root'
		super(RootFolder, self).__init__(*args, **kwargs)
