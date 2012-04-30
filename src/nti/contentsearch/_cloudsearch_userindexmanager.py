#import contextlib

from zope import component
from zope import interface

from nti.dataserver import interfaces as nti_interfaces
from nti.externalization.oids import toExternalOID
#from nti.externalization.oids import fromExternalOID
from nti.externalization.externalization import toExternalObject

from nti.contentsearch.exfm.cloudsearch import get_document_service

from nti.contentsearch import interfaces
from nti.contentsearch import QueryObject
from nti.contentsearch import SearchCallWrapper
#from nti.contentsearch.interfaces import IUserIndexManagerFactory
from nti.contentsearch.common import is_all_query
from nti.contentsearch.common import get_type_name
from nti.contentsearch.common import get_last_modified
from nti.contentsearch.common import normalize_type_name

#from nti.contentsearch.common import empty_search_result
#from nti.contentsearch.common import empty_suggest_result
#from nti.contentsearch._repoze_query import parse_query
#from nti.contentsearch._search_external import get_search_hit
from nti.contentsearch.common import (WORD_HIGHLIGHT, NGRAM_HIGHLIGHT)
from nti.contentsearch.common import (LAST_MODIFIED, username_, content_)

import logging
logger = logging.getLogger( __name__ )

class CloudSearchUserIndexManager(object):
	interface.implements(interfaces.IUserIndexManager)

	def __init__(self, username):
		self.username = username

	def __str__( self ):
		return self.username

	def __repr__( self ):
		return 'CloudSearchUserIndexManager(user=%s)' % self.username

	def get_username(self):
		return self.username
	
	@property
	def dataserver(self):
		return component.getUtility( nti_interfaces.IDataserver )

	def _adapt_search_on_types(self, search_on=None):
		if search_on:
			search_on = [normalize_type_name(x) for x in search_on]
		return search_on or self.store.get_catalog_names(self.username)
	
	def _get_document_service(self, endpoint=None):
		return get_document_service(endpoint=endpoint)
	
	def _do_search(self, field, qo, search_on, highlight_type):
		query = "username:'%s'" % self.username
	
	@SearchCallWrapper
	def search(self, query, *args, **kwargs):
		qo = QueryObject.create(query, **kwargs)
		search_on = self._adapt_search_on_types(qo.search_on)
		highlight_type = None if is_all_query(qo.term) else WORD_HIGHLIGHT
		results = self._do_search(content_, qo, search_on, highlight_type)
		return results
	
	def index_content(self, data, type_name=None, **kwargs):
		if not data: return None
		
		service = self._get_document_service()
		
		type_name = normalize_type_name(type_name or get_type_name(data))
		oid  = toExternalOID(data)
		data = toExternalObject(data)
		
		# make sure the user name is always set
		data[username_] = self.username
		
		# get and update the last modified data
		# cs supports uint ony and we use this number as version also
		lm = int(get_last_modified(data)) 
		data[LAST_MODIFIED] = lm
		
		# set 0 as version s
		service.add(oid, 0, data) 
		result = service.commit()
		if result.errors:
			s = ' '.join(result.errors)
			raise Exception(s)
		return result
	
	update_content = index_content

	def delete_content(self, data, type_name=None, *args, **kwargs):
		if not data: return None
		service = self._get_document_service()
		oid = toExternalOID(data)
		service.delete(oid, 0) 
		result = service.commit()
		if result.errors:
			s = ' '.join(result.errors)
			logger.error(s)
			return False
		return True

	
