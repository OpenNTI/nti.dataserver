# -*- coding: utf-8 -*-
"""
Base entity search manager

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface
from zope.container import contained as zcontained
from zope.interface.common.mapping import IMapping

from ZODB import loglevels

from persistent.mapping import PersistentMapping

from nti.dataserver import interfaces as nti_interfaces

from nti.chatserver import interfaces as chat_interfaces

from . import interfaces as search_interfaces
from . import _discriminators as discriminators

@interface.implementer(search_interfaces.IEntityIndexManager, IMapping)
class _SearchEntityIndexManager(zcontained.Contained, PersistentMapping):

	@property
	def entity(self):
		return self.__parent__

	@property
	def username(self):
		return self.entity.username

	def get_username(self):
		return self.username

	def get_uid(self, obj):
		return discriminators.get_uid(obj)

	def get_object(self, uid):
		result = discriminators.query_object(uid,)
		if result is None:
			logger.debug('Could not find object with id %r' % uid)

		if result is not None and not self.verify_access(result):
			logger.log(loglevels.TRACE, '%s does not have access to %s', self.username, result)
			result = None

		return result

	def verify_access(self, obj):
		result = chat_interfaces.IMessageInfo.providedBy(obj) or \
				 (nti_interfaces.IShareableModeledContent.providedBy(obj) and obj.isSharedDirectlyWith(self.entity))

		if not result:
			index_owner = self.username.lower()
			adapted = component.getAdapter(obj, search_interfaces.IShareableContentResolver)
			creator = adapted.get_creator().lower()
			sharedWith = {x.lower() for x in adapted.get_sharedWith() or ()}
			result = index_owner == creator or index_owner in sharedWith

		return result

	def search(self, query):
		raise NotImplementedError()

	def suggest(self, query):
		raise NotImplementedError()

	def suggest_and_search(self, query):
		raise NotImplementedError()

	def index_content(self, data, type_name=None):
		raise NotImplementedError()

	def update_content(self, data, type_name=None):
		raise NotImplementedError()

	def delete_content(self, data, type_name=None):
		raise NotImplementedError()

	def remove_index(self, type_name):
		raise NotImplementedError()

	def __repr__(self):
		return '%s(%s, %s)' % (self.__class__.__name__, self.username, self.keys())
