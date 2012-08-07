from __future__ import print_function, unicode_literals

import zope.intid
from zope import component
from zope import interface
from zope.location.interfaces import ILocation

from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch import interfaces

import logging
logger = logging.getLogger( __name__ )

class _SearchUserIndexManager(object):
	interface.implements(interfaces.IUserIndexManager, ILocation)
	
	def get_uid(self, obj):
		_ds_intid = component.getUtility( zope.intid.IIntIds )
		return _ds_intid.getId(obj)
	
	def get_object(self, uid):
		_ds_intid = component.getUtility( zope.intid.IIntIds )
		return _ds_intid.getObject(uid)
		
	@property
	def dataserver(self):
		return component.getUtility( nti_interfaces.IDataserver )

	def search(self, query, *args, **kwargs):
		raise NotImplementedError()

	def ngram_search(self, query, *args, **kwargs):
		raise NotImplementedError()
	quick_search = ngram_search

	def suggest(self, query, *args, **kwargs):
		raise NotImplementedError()

	def suggest_and_search(self, query, limit=None, *args, **kwargs):
		raise NotImplementedError()
	
	def index_content(self, data, type_name=None, **kwargs):
		raise NotImplementedError()

	def update_content(self, data, type_name=None, *args, **kwargs):
		raise NotImplementedError()

	def delete_content(self, data, type_name=None, *args, **kwargs):
		raise NotImplementedError()

	def remove_index(self, type_name):
		raise NotImplementedError()
		
	def get_stored_indices(self):
		raise NotImplementedError()
			
	
