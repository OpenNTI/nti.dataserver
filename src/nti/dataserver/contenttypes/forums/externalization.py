#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Externalization for forum objects.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.common.dataurl import encode
from nti.common.mimetypes import guess_type

from nti.dataserver.interfaces import IThreadable

from nti.dataserver.contenttypes.base import UserContentRootInternalObjectIOMixin

from nti.dataserver.contenttypes.forums.interfaces import IPost
from nti.dataserver.contenttypes.forums.interfaces import IBoard
from nti.dataserver.contenttypes.forums.interfaces import IForum
from nti.dataserver.contenttypes.forums.interfaces import ITopic

from nti.dataserver.contenttypes.threadable import ThreadableExternalizableMixin

from nti.dataserver.users import Entity

from nti.externalization.externalization import to_external_object

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IInternalObjectExternalizer

from nti.mimetype import decorateMimeType

from nti.namedfile.interfaces import INamedFile

ITEMS = StandardExternalFields.ITEMS
MIMETYPE = StandardExternalFields.MIMETYPE

class _MaybeThreadableForumObjectInternalObjectIO(ThreadableExternalizableMixin,
												  UserContentRootInternalObjectIOMixin):
	"""
	Some of our objects are threadable, some are not, so
	we distinguish here. This was easier than registering custom
	objects for the specific interfaces.

	.. note: We are not enforcing that replies are to objects in the same topic.
	"""

	def _ext_can_write_threads(self):
		return IThreadable.providedBy(self._ext_replacement())

	def _ext_can_update_threads(self):
		return (super(_MaybeThreadableForumObjectInternalObjectIO, self)._ext_can_update_threads()
				and IThreadable.providedBy(self._ext_replacement()))

@interface.implementer(IInternalObjectExternalizer)
class _BaseExporter(object):

	def handle_sharedWith(self, result):
		sharedWith = result.get('sharedWith')
		for idx, name in enumerate(sharedWith or ()):
			entity = Entity.get_entity(name)
			if entity is not None:
				sharedWith[idx] = to_external_object(entity,
													 name='summary',
													 decorate=False)

@component.adapter(IPost)
class _PostExporter(_BaseExporter):

	def __init__(self, obj):
		self.post = obj

	def toExternalObject(self, **kwargs):
		mod_args = dict(**kwargs)
		mod_args['name'] = ''  # set default
		mod_args['decorate'] = False  # no decoration
		result = to_external_object(self.post, **mod_args)
		if MIMETYPE not in result:
			decorateMimeType(self.post, result)
		self.handle_sharedWith(result)
		items = {}
		for value in self.post.body or ():
			if not INamedFile.providedBy(value):
				continue
			name = value.filename or value.name
			mimeType = guess_type(name)[0] or u'application/octet-stream'
			items[name] = [encode(value.data, mimeType)]
		if items:
			result['Files'] = items
		return result

@component.adapter(ITopic)
class _TopicExporter(_BaseExporter):

	def __init__(self, obj):
		self.topic = obj

	def toExternalObject(self, **kwargs):
		mod_args = dict(**kwargs)
		mod_args['name'] = ''  # set default
		mod_args['decorate'] = False  # no decoration
		result = to_external_object(self.topic, **mod_args)
		if MIMETYPE not in result:
			decorateMimeType(self.topic, result)
		self.handle_sharedWith(result)
		result.pop('PostCount', None)
		result.pop('NewestDescendant', None)
		result.pop('NewestDescendantCreatedTime', None)
		items = []  # export posts
		mod_args['name'] = 'exporter'
		for post in sorted(self.topic.values(), key=lambda x:x.createdTime):
			ext_obj = to_external_object(post, **mod_args)
			items.append(ext_obj)
		if items:
			result[ITEMS] = items
		return result

@component.adapter(IForum)
class _ForumExporter(_BaseExporter):

	def __init__(self, obj):
		self.forum = obj

	def toExternalObject(self, **kwargs):
		mod_args = dict(**kwargs)
		mod_args['name'] = ''  # set default
		mod_args['decorate'] = False  # no decoration
		result = to_external_object(self.forum, **mod_args)
		if MIMETYPE not in result:
			decorateMimeType(self.forum, result)
		self.handle_sharedWith(result)
		result.pop('TopicCount', None)
		result.pop('NewestDescendant', None)
		result.pop('NewestDescendantCreatedTime', None)
		items = []  # export topics
		mod_args['name'] = 'exporter'
		for topic in sorted(self.forum.values(), key=lambda x:x.createdTime):
			ext_obj = to_external_object(topic, **mod_args)
			items.append(ext_obj)
		if items:
			result[ITEMS] = items
		return result

@component.adapter(IBoard)
class _BoardExporter(_BaseExporter):

	def __init__(self, obj):
		self.board = obj

	def toExternalObject(self, **kwargs):
		mod_args = dict(**kwargs)
		mod_args['name'] = ''  # set default
		mod_args['decorate'] = False  # no decoration
		result = to_external_object(self.board, **mod_args)
		if MIMETYPE not in result:
			decorateMimeType(self.board, result)
		self.handle_sharedWith(result)
		result.pop('ForumCount', None)
		items = []  # export forum
		mod_args['name'] = 'exporter'
		for forum in sorted(self.board.values(), key=lambda x:x.createdTime):
			ext_obj = to_external_object(forum, **mod_args)
			items.append(ext_obj)
		if items:
			result[ITEMS] = items
		return result
