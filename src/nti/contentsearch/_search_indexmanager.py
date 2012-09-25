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
		result = _ds_intid.queryObject(uid, None)
		if result is None:
			logger.debug('Could not find object with id %r' % uid)
		return result
		
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
			
	
