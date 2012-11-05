from __future__ import print_function, unicode_literals

from zope import component
from zope import interface
from zope.annotation import factory as an_factory
from zope.interface.common.mapping import IFullMapping

from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch._repoze_adpater import _BaseRepozeEntityIndexManager

import logging
logger = logging.getLogger( __name__ )

@component.adapter(nti_interfaces.IEntity)
@interface.implementer( search_interfaces.IRepozeRedisEntityIndexManager, IFullMapping)
class _RepozeRedisEntityIndexManager(_BaseRepozeEntityIndexManager):

	_v_service = None
	
	def _get_service(self):
		if self._v_service is None:
			self._v_service = component.getUtility(search_interfaces.IRepozeStoreService)
		return self._v_service
	
	def index_content(self, data, type_name=None):
		if not data: return False
		docid = self.get_uid(data)
		service = self._get_service()
		service.add(docid, username=self.username)
		return True

	def update_content(self, data, type_name=None):
		if not data: return False
		docid = self.get_uid(data)
		service = self._get_service()
		service.update(docid, username=self.username)
		return True

	def delete_content(self, data, type_name=None):
		if not data: return False
		docid = self.get_uid(data)
		service = self._get_service()
		service.delete(docid, username=self.username)
		return True

def _RepozeRedisEntityIndexManagerFactory(entity):
	result = an_factory(_RepozeRedisEntityIndexManager)(entity)
	return result
