import gevent

from zope import component
from zope import interface
from zope.component.hooks import site
from zope.component.interfaces import ISite

from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch import QueryObject
from nti.contentsearch import interfaces
from nti.contentsearch import SearchCallWrapper
from nti.contentsearch._indexagent import handle_index_event

from nti.contentsearch.common import empty_search_result
from nti.contentsearch.common import empty_suggest_result
from nti.contentsearch.common import merge_search_results
from nti.contentsearch.common import merge_suggest_results
from nti.contentsearch.common import empty_suggest_and_search_result
from nti.contentsearch.common import merge_suggest_and_search_results

import logging
logger = logging.getLogger( __name__ )

# -----------------------------

class _FakeSite(object):
	interface.implements(ISite)
	
	def __init__(self, sitemanager):
		self.sitemanager = sitemanager
				
	def setSiteManager(self, sitemanager):
		self.sitemanager = sitemanager

	def getSiteManager(self):
		return self.sitemanager

def _greenlet_spawn(func, *args, **kwargs):
	local_site = _FakeSite(component.getSiteManager())
	def runner(f, *fargs, **fkwargs):
		with site(local_site):
			return f(*fargs, **fkwargs)
	greenlet = gevent.spawn(runner, f=func, *args, **kwargs)
	return greenlet

# -----------------------------------
	
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

	def __init__(self, bookidx_manager_factory, useridx_manager_factory, max_users=500, *args, **kwargs):
		self.books = {}
		self.bookidx_manager_factory = bookidx_manager_factory
		self.useridx_manager_factory = useridx_manager_factory

	def __str__( self ):
		return self.__repr__()

	def __repr__( self ):
		return 'IndexManager(books=%s, %s)' % (len(self.books), self.useridx_manager_factory)

	@property
	def dataserver(self):
		return component.queryUtility( nti_interfaces.IDataserver )

	def users_exists(self, username):
		result = User.get_user(username, dataserver=self.dataserver) if self.dataserver else None
		return result is not None

	# -------------------
	
	@SearchCallWrapper
	def search(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		username = query.username
	
		jobs = []
		try:
			# search user contentc
			self._ugd_search_jobs(query, jobs) if username else []
		
			logger.info("\nMY BOOKS %s" % self.books)
			logger.info("HERE %s" % query.books)
			# search books
			for indexname in query.books:
				job = _greenlet_spawn(func=self.content_search, indexname=indexname, query=query)
				jobs.append(job)
		finally:
			gevent.joinall(jobs)
		
		# merge results
		results = None
		for job in jobs:
			results = merge_search_results (results, job.value)
		return results
		
	@SearchCallWrapper
	def ngram_search(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		username = query.username
		
		jobs = []
		try:
			# search user content
			self._ugd_ngram_search_jobs(query, jobs) if username else []
		
			# search books
			for indexname in query.books:
				job = _greenlet_spawn(func=self.content_ngram_search, indexname=indexname, query=query)
				jobs.append(job)
		finally:
			gevent.joinall(jobs)
		
		# merge results
		results = None
		for job in jobs:
			results = merge_search_results (results, job.value)
		return results
		
	@SearchCallWrapper
	def suggest_and_search(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		username = query.username
		
		jobs = []
		try:
			# search user content
			self._ugd_suggest_and_search_jobs(query, jobs) if username else []
		
			# search books
			for indexname in query.books:
				job = _greenlet_spawn(func=self.content_suggest_and_search, indexname=indexname, query=query)
				jobs.append(job)
		finally:
			gevent.joinall(jobs)
		
		# merge results
		results = None
		for job in jobs:
			results = merge_suggest_and_search_results(results, job.value)
		return results
	
	@SearchCallWrapper
	def suggest(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		username = query.username
		
		jobs = []
		try:
			# search user content
			self._ugd_suggest_jobs(query, jobs) if username else []
		
			# search books
			for indexname in query.books:
				job = _greenlet_spawn(func=self.content_suggest, indexname=indexname, query=query)
				jobs.append(job)
		finally:
			gevent.joinall(jobs)
		
		# merge results
		results = None
		for job in jobs:
			results = merge_suggest_results(results, job.value)
		return results
	
	# -------------------

	def get_book_index_manager(self, indexname):
		return self.books.get(indexname, None)

	def add_book(self, indexname, *args, **kwargs):
		result = False
		if not self.books.has_key(indexname):
			logger.info("ADDING BOOK %s, %s" % (indexname, kwargs))
			bmi = self.bookidx_manager_factory(indexname=indexname, **kwargs)
			logger.info("BMI IS %s" % bmi)
			if bmi:
				self.books[indexname] = bmi
				result = True
		return result

	def content_search(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		bm = self.get_book_index_manager(query.indexname)
		results = bm.search(query) if (bm and not query.is_empty) else None
		return results if results else empty_search_result(query.term)

	def content_ngram_search(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		bm = self.get_book_index_manager(query.indexname)
		results = bm.ngram_search(query) if (bm and not query.is_empty) else None
		return results if results else empty_search_result(query.term)

	def content_suggest_and_search(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		bm = self.get_book_index_manager(query.indexname)
		results = bm.suggest_and_search(query) if (bm and not query.is_empty) else None
		return results if results else empty_suggest_and_search_result(query.term)

	def content_suggest(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		bm = self.get_book_index_manager(query.indexname)
		results = bm.suggest(query) if (bm and not query.is_empty) else None
		return results if results else empty_suggest_result(query.term)

	quick_search = content_ngram_search
	content_quick_search = content_ngram_search
	
	# -------------------

	def _get_user_index_manager(self, username, create=False):
		result = None
		if self.users_exists(username):
			result = self.useridx_manager_factory(username=username, create=create)
		return result

	def _get_user_object(self, username):
		result = User.get_user(username, dataserver=self.dataserver) if self.dataserver else None
		return result

	def _get_user_communities(self, username):
		user = self._get_user_object(username)
		return list(user.communities) if user else []

	def _get_search_uims(self, username):
		result = []
		for name in [username] + self._get_user_communities(username):
			uim = self._get_user_index_manager(name)
			if uim: result.append(uim)
		return result
		
	# -------------------
	
	def _ugd_search_jobs(self, query, jobs=[]):
		for uim in self._get_search_uims(query.username):
			job = _greenlet_spawn(func=uim.search, query=query)
			jobs.append(job)
		return jobs
		
	def user_data_search(self, query, *args, **kwargs):
		results = None
		query = QueryObject.create(query, **kwargs)
		if not query.is_empty:
			jobs = []
			try:
				self._ugd_search_jobs(query,jobs)
			finally:
				gevent.joinall(jobs)
			for job in jobs:
				results = merge_search_results(results, job.value)
		return results if results else empty_search_result(query.term)

	# ------------
	
	def _ugd_ngram_search_jobs(self, query, jobs=[]):
		for uim in self._get_search_uims(query.username):
			job = _greenlet_spawn(func=uim.ngram_search, query=query)
			jobs.append(job)
		return jobs
	
	def user_data_ngram_search(self, query, *args, **kwargs):
		results = None
		query = QueryObject.create(query, **kwargs)
		if not query.is_empty:
			jobs = []
			try:
				self._ugd_ngram_search_jobs(query, jobs)
			finally:
				gevent.joinall(jobs)
			for job in jobs:
				results = merge_search_results (results, job.value)
		return results if results else empty_search_result(query.term)

	user_data_quick_search = user_data_ngram_search
	
	# ------------
	
	def _ugd_suggest_and_search_jobs(self, query, jobs=[]):
		for uim in self._get_search_uims(query.username):
			job = _greenlet_spawn(func=uim.suggest_and_search, query=query)
			jobs.append(job)
		return jobs
	
	def user_data_suggest_and_search(self, query, *args, **kwargs):
		results = None
		query = QueryObject.create(query, **kwargs)
		if not query.is_empty:
			jobs = []
			try:
				self._ugd_suggest_and_search_jobs(query, jobs)
			finally:
				gevent.joinall(jobs)
			for job in jobs:
				results = merge_suggest_and_search_results (results, job.value)
		return results if results else empty_suggest_and_search_result(query.term)

	# ------------
	
	def _ugd_suggest_jobs(self, query, jobs=[]):
		for uim in self._get_search_uims(query.username):
			job = _greenlet_spawn(func=uim.suggest, query=query)
			jobs.append(job)
		return jobs
	
	def user_data_suggest(self, query, *args, **kwargs):
		results = None
		query = QueryObject.create(query, **kwargs)
		if not query.is_empty:
			jobs = []
			try:
				self._ugd_suggest_jobs(query, jobs)
			finally:
				gevent.joinall(jobs)
			for job in jobs:
				results = merge_suggest_results(results, job.value)
		return results if results else empty_suggest_result(query)

	# -------------------
	
	def _get_data(self, kwargs):
		if 'data' in kwargs:
			result = kwargs.pop('data')
		else:
			result = kwargs.get('externalValue', None)
		return result

	def index_user_content(self, username, type_name=None, *args, **kwargs):
		data = self._get_data(kwargs)
		um = None
		if data:
			um = self._get_user_index_manager(username, create=True)
		if um and data:
			return um.index_content(data, type_name, *args, **kwargs)

	def update_user_content(self, username, type_name=None, *args, **kwargs):
		data = self._get_data(kwargs)
		um = None
		if data:
			um = self._get_user_index_manager(username,create=True)
		if um and data:
			return um.update_content(data, type_name, *args, **kwargs)

	def delete_user_content(self, username, type_name=None, *args, **kwargs):
		data = self._get_data(kwargs)
		um = None
		if data:
			um = self._get_user_index_manager(username,create=True)
		if um and data:
			return um.delete_content(data, type_name, *args, **kwargs)

	@classmethod
	def onChange(cls, datasvr, msg, username=None, broadcast=None):
		handle_index_event(cls.get_shared_indexmanager(), username, msg)

	# -------------------

	def close(self):
		for bm in self.books.itervalues():
			self._close(bm)

	def __del__(self):
		self.close()
