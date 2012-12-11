from __future__ import print_function, unicode_literals

import zope.intid
from zope import component
from zope import interface
from zope.location.interfaces import ILocation
from zope.interface.common.mapping import IMapping

from persistent.mapping import PersistentMapping

from nti.dataserver import interfaces as nti_interfaces

from nti.chatserver import interfaces as chat_interfaces

from nti.contentsearch import interfaces as search_interfaces

import logging
logger = logging.getLogger( __name__ )

@interface.implementer( search_interfaces.IEntityIndexManager, ILocation, IMapping)
class _SearchEntityIndexManager(PersistentMapping):
	
	@property
	def entity(self):
		return self.__parent__
	
	@property
	def username(self):
		return self.entity.username
	
	def get_username(self):
		return self.username
	
	def get_uid(self, obj):
		_ds_intid = component.getUtility( zope.intid.IIntIds )
		return _ds_intid.getId(obj)
	
	def get_object(self, uid):
		_ds_intid = component.getUtility( zope.intid.IIntIds )
		result = _ds_intid.queryObject(int(uid), None)
		if result is None:
			logger.debug('Could not find object with id %r' % uid)
			
		if result is not None and not self.verify_access(result):
			result = None
	
		return result
		
	def verify_access(self, obj):
		result = chat_interfaces.IMessageInfo.providedBy(obj) or \
				 (nti_interfaces.IShareableModeledContent.providedBy(obj) and obj.isSharedDirectlyWith(self.entity))

		if not result:
			index_owner = self.username.lower()
			adapted = component.getAdapter(obj, search_interfaces.IThreadableContentResolver)
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

