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
from zope import lifecycleevent

from zope.mimetype.interfaces import IContentTypeAware

from nti.common.property import alias

from nti.coremetadata.interfaces import SYSTEM_USER_ID

from nti.containers.containers import CaseInsensitiveCheckingLastModifiedBTreeContainer

from nti.contentfolder.interfaces import IRootFolder
from nti.contentfolder.interfaces import IContentFolder
from nti.contentfolder.interfaces import INamedContainer

from nti.namedfile.file import get_file_name

from nti.namedfile.interfaces import IFile

from nti.schema.fieldproperty import createDirectFieldProperties

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

@interface.implementer(IContentFolder, IContentTypeAware)
class ContentFolder(CaseInsensitiveCheckingLastModifiedBTreeContainer):
	createDirectFieldProperties(IContentFolder)

	__parent__ = None
	name = alias('__name__')

	creator = None
	parameters = {}
	mimeType = mime_type = str('application/vnd.nextthought.contentfolder')

	path = None # BWC

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

	def remove(self, obj):
		name = get_context_name(obj)
		if not name:
			return False
		if name in self:
			del self[name]
			return True
		return False

	def rename(self, old, new):
		assert 		isinstance(old, six.string_types) \
				or	INamedContainer.providedBy(old) \
				or	IFile.providedBy(old)

		name = get_context_name(old) or old
		item = self._delitemf(name, event=False)
		item.name = new # set new name
		self._setitemf(new, item)

	def moveTo(self, item, target, newName=None):
		assert 		isinstance(item, six.string_types) \
				or	INamedContainer.providedBy(item) \
				or	IFile.providedBy(item)

		assert INamedContainer.providedBy(target)
		if self == target:
			return False

		# check item exists in this continer
		name = get_context_name(item) or item
		if name not in self:
			return False
		newName = newName or name

		# remove from target if found
		if newName in target:
			del target[newName]

		item = self._delitemf(name, event=False)
		item.name = newName # set new name
		target._setitemf(newName, item)

		lifecycleevent.moved(item, self, name, target, newName)
		return True
	
	# compatible methods

	def getChildNamed(self, key):
		try:
			result = self[key]
		except KeyError:
			result = None
		return result

	def enumerateChildren(self):
		return tuple(self.keys())

@interface.implementer(IRootFolder)
class RootFolder(ContentFolder):
	createDirectFieldProperties(IRootFolder)

	__external_can_create__ = False

	creator = SYSTEM_USER_ID
	mimeType = mime_type = str('application/vnd.nextthought.contentrootfolder')

	def __init__(self, *args, **kwargs):
		kwargs['name'] = kwargs.get('name') or 'root'
		super(RootFolder, self).__init__(*args, **kwargs)
