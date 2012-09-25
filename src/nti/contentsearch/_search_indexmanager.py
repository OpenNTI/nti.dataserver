from __future__ import print_function, unicode_literals

import zope.intid
from zope import component
from zope import interface
from zope.location.interfaces import ILocation

from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch import interfaces as search_interfaces

import logging
logger = logging.getLogger( __name__ )

class _SearchEntityIndexManager(object):
	interface.implements(search_interfaces.IEntityIndexManager, ILocation)
	
	def get_uid(self, obj):
		_ds_intid = component.getUtility( zope.intid.IIntIds )
		return _ds_intid.getId(obj)
	
	def get_object(self, uid, ignore_exp=False):
		_ds_intid = component.getUtility( zope.intid.IIntIds )
		try:
			return _ds_intid.getObject(uid)
		except Exception:
			if not ignore_exp:
				raise
			logger.warn('Could not find object with id %r' % uid)
			return None
		
	def get_object_safe(self, uid):
		return self.get_object(uid, True)
	
	@property
	def dataserver(self):
		return component.getUtility( nti_interfaces.IDataserver )

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
		
	def get_stored_indices(self):
		raise NotImplementedError()
			
	
