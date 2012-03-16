import gevent

from zope import component
from zope import interface

from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch import LFUMap
from nti.contentsearch import interfaces
from nti.contentsearch._indexagent import IndexAgent
from nti.contentsearch.common import empty_search_result
from nti.contentsearch.common import empty_suggest_result
from nti.contentsearch.common import merge_search_results
from nti.contentsearch.common import merge_suggest_results
from nti.contentsearch.common import empty_suggest_and_search_result
from nti.contentsearch.common import merge_suggest_and_search_results

import logging
logger = logging.getLogger( __name__ )

# -----------------------------

class IndexManager(object):
	interface.implements(interfaces.IIndexManager)
	
	# -------------------
	
	indexmanager = None

	@classmethod
	def get_shared_indexmanager(cls):
		return cls.indexmanager

	def __new__(cls, *args, **kwargs):
		if not cls.indexmanager:
			cls.indexmanager = super(IndexManager, cls).__new__(cls, *args, **kwargs)
		return cls.indexmanager
	
	def __init__(self, bookidx_manager_factory, useridx_manager_factory, max_users=100, dataserver=None):
		self.books = {}
		self._indexagent = IndexAgent( self )
		self.users = LFUMap(maxsize=max_users, on_removal_callback=self.on_item_removed)
		self.bookidx_manager_factory = bookidx_manager_factory
		self.useridx_manager_factory = useridx_manager_factory
		self.ds = dataserver or component.queryUtility( nti_interfaces.IDataserver )
	
	@property
	def dataserver(self):
		return self.ds
	
	# -------------------
	
	def get_book_index_manager(self, indexname):
		return self.books.get(indexname, None)
	
	def add_book(self, indexname, *args, **kwargs):
		result = False
		if not self.books.has_key(indexname):
			bmi = self.bookidx_manager_factory(index=indexname, **kwargs)
			if bmi:
				self.books[indexname] = bmi
				result = True
		return result

	def content_search(self, indexname, query, limit=None, *args, **kwargs):
		bm = self.get_book_index_manager(indexname)
		results = bm.search(query, limit, *args, **kwargs) if (bm and query) else None
		return results if results else empty_search_result(query)
	
	def content_ngram_search(self, indexname, query, limit=None, *args, **kwargs):
		bm = self.get_book_index_manager(indexname)
		results = bm.ngram_search(query, limit, *args, **kwargs) if (bm and query) else None
		return results if results else empty_search_result(query)
		
	def content_suggest_and_search(self, indexname, query, limit=None, *args, **kwargs):
		bm = self.get_book_index_manager(indexname)
		results = bm.suggest_and_search(query, limit, *args, **kwargs) if (bm and query) else None
		return results if results else empty_suggest_and_search_result(query)
		
	def content_suggest(self, indexname, term, limit=None, prefix=None, *args, **kwargs):
		bm = self.get_book_index_manager(indexname)
		results = bm.suggest(term, limit=limit, prefix=prefix, **kwargs) if (bm and term) else None
		return results if results else empty_suggest_result(term)
			
	search = content_search
	suggest = content_suggest
	quick_search = content_search
	content_quick_search = content_ngram_search
	suggest_and_search = content_suggest_and_search
		
	# -------------------

	def _get_user_index_manager(self, username):
		uim = self.users.get(username, None)
		if not uim:
			uim = self.useridx_manager_factory(username=username)
			if uim:
				self.users[username] = uim
		return uim

	def _get_user_object(self, username):
		result = None
		if self.dataserver:
			with self.dataserver.dbTrans():
				result = self.dataserver.root['users'].get(username, None)
		return result
	
	def _get_user_communities(self, username):
		user = self._get_user(username)
		return list(user.communities) if user else []

	def _get_search_uims(self, username):
		result = []
		for name in [username] + self.get_user_communities(username):
			uim = self._get_user_index_manager(name)
			if uim: result.append(uim)
		return result

	def user_data_search(self, username, query, limit=None, *args, **kwargs):
		results = None
		if query:
			jobs = []
			for uim in self._get_search_uims(username):
				jobs.append(gevent.spawn(uim.search, query=query, limit=limit, **kwargs))
			gevent.joinall(jobs)
			for job in jobs:
				results = merge_search_results (results, job.value)
		return results if results else empty_search_result(query)

	def user_data_ngram_search(self, username, query, limit=None, *args, **kwargs):
		results = None
		if query:
			jobs = []
			for uim in self._get_search_uims(username):
				jobs.append(gevent.spawn(uim.ngram_search, query=query, limit=limit, **kwargs))
			gevent.joinall(jobs)
			for job in jobs:
				results = merge_search_results (results, job.value)
		return results if results else empty_search_result(query)

	def user_data_suggest_and_search(self, username, query, limit=None, *args, **kwargs):
		results = None
		if query:
			jobs = []
			for uim in self._get_search_uims(username):
				jobs.append(gevent.spawn(uim.suggest_and_search, query=query, limit=limit, **kwargs))
			gevent.joinall(jobs)
			for job in jobs:
				results = merge_suggest_and_search_results (results, job.value)
		return results if results else empty_suggest_and_search_result(query)

	def user_data_suggest(self, username, term, limit=None, prefix=None, *args, **kwargs):
		results = None
		if term:
			jobs = []
			for uim in self._get_search_uims(username):
				jobs.append(gevent.spawn(uim.suggest, term, limit=limit, prefix=prefix, **kwargs))
			gevent.joinall(jobs)
			for job in jobs:
				results = merge_suggest_results (results, job.value)
		return results if results else empty_suggest_result(term)

	user_data_quick_search = user_data_ngram_search
	
	# -------------------
	
	def index_user_content(self, username, data, type_name=None, *args, **kwargs):
		um = self._get_user_index_manager(username)
		if um: um.index_content(data, type_name, *args, **kwargs)

	def update_user_content(self, username, data, type_name=None, *args, **kwargs):
		um = self._get_user_index_manager(username)
		if um: um.update_content(data, type_name, *args, **kwargs)

	def delete_user_content(self, username, data, type_name=None, *args, **kwargs):
		um = self._get_user_index_manager(username)
		if um: um.delete_content(data, type_name, *args, **kwargs)
		
	# -------------------

	@classmethod
	def onChange(cls, datasvr, msg, username=None, broadcast=None):
		if username:
			obj = getattr(msg, "object", None)
			if obj:
				data = obj
				if callable( getattr( obj, 'toExternalObject', None ) ):
					data = obj.toExternalObject()
				cls.get_shared_indexmanager()._indexagent.add_event(creator = username,
																	changeType = msg.type,
																	dataType = obj.__class__.__name__,
																	data=data )

	# -------------------

	def _close(self, obj):
		if obj and hasattr(obj, 'close'):
			try:
				obj.close()
			except:
				pass
			
	def on_item_removed(self, key, value):
		self._close(value)
		
	def remove_user(self, username):
		um = self.users.pop(username, None)
		self._close(um)

	def _close_ums(self):
		for um in self.users.itervalues():
			self._close(um)
	
	def close(self):
		for bm in self.books.itervalues():
			self._close(bm)
			
		self._close_ums()
		self._indexagent.close()

	def __del__(self):
		self.close()

# -----------------------------

import _whoosh_bookindexmanager
import _whoosh_userindexmanager
from indexstorage import MultiDirectoryStorage

def create_index_manager(dataserver=None):
	mds = MultiDirectoryStorage("/tmp")
	umf = _whoosh_userindexmanager.wuim_factory(mds, use_md5=False)
	bmf = _whoosh_bookindexmanager.wbm_factory()
	return IndexManager(bmf, umf, dataserver=dataserver)
