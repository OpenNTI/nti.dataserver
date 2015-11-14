#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six

from zope import interface

from nti.common.property import alias

from nti.coremetadata.interfaces import SYSTEM_USER_ID

from nti.namedfile.file import get_file_name

from nti.containers.containers import CaseInsensitiveCheckingLastModifiedBTreeContainer

from nti.schema.fieldproperty import createDirectFieldProperties

from .interfaces import IRootFolder
from .interfaces import IContentFolder
from .interfaces import INamedContainer

def checkValidId(uid):

	if not uid or not isinstance(uid, six.string_types):
		raise ValueError('Empty or invalid id specified', uid)

	if uid in ('.', '..'):
		raise ValueError('The id "%s" is invalid because it is not traversable.' % uid)

	if '/' in uid:
		raise ValueError('The id "%s" contains characters illegal.' % uid)

def get_context_name(context):
	if INamedContainer.providedBy(context):
		result = context.name
	else:
		result = get_file_name(context)
	return result

@interface.implementer(IContentFolder)
class ContentFolder(CaseInsensitiveCheckingLastModifiedBTreeContainer):

	createDirectFieldProperties(IContentFolder)

	__parent__ = None
	name = alias('__name__')

	creator = None
	parameters = {}
	mimeType = mime_type = str('application/vnd.nextthought.contentfolder')

	def __init__(self, *args, **kwargs):
		super(ContentFolder, self).__init__()
		self.name = kwargs.get('name')
		self.use_blobs = kwargs.get('use_blobs', True)
		self.title = kwargs.get('title') or self.name
		self.description = kwargs.get('description') or self.title

	def __setitem__(self, key, value):
		checkValidId(key)
		CaseInsensitiveCheckingLastModifiedBTreeContainer.__setitem__(self, key, value)

	def add(self, obj):
		name = get_context_name(obj)
		if not name:
			raise ValueError("Cannot get file name")
		if name in self:
			del self[name]
		self[name] = obj
		return obj
	append = add

@interface.implementer(IRootFolder)
class RootFolder(ContentFolder):
	createDirectFieldProperties(IRootFolder)

	__external_can_create__ = False

	parameters = {}
	creator = SYSTEM_USER_ID
	mimeType = mime_type = str('application/vnd.nextthought.contentrootfolder')

	def __init__(self, *args, **kwargs):
		kwargs['name'] = kwargs.get('name') or 'root'
		super(RootFolder, self).__init__(*args, **kwargs)
