# -*- coding: utf-8 -*-
"""
Whoosh based book index manager

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

try:
	from gevent.lock import BoundedSemaphore
except ImportError:
	from threading import BoundedSemaphore

from zope import interface
from zope.proxy import ProxyBase

from perfmetrics import metric

from whoosh import index

from ._whoosh_index import Book
from ._search_query import QueryObject
from . import interfaces as search_interfaces
from ._whoosh_indexstorage import DirectoryStorage
from ._whoosh_query import CosineScorerModel as CSM

class _BoundingProxy(ProxyBase):

	_max_searchers = 256 # Max number of searchers. Set in a config?
	_semaphore = BoundedSemaphore(_max_searchers)

	def __init__(self, obj):
		super(_BoundingProxy, self).__init__(obj)
		self.obj = obj

	def __enter__(self):
		self._semaphore.acquire()
		return self.obj.__enter__()

	def __exit__(self, *args, **kwargs):
		result = None
		try:
			result = self.obj.__exit__(*args, **kwargs)
		finally:
			self._semaphore.release()
		return result

@interface.implementer( search_interfaces.IWooshBookIndexManager )
class WhooshBookIndexManager(object):

	def __init__(self, indexname, ntiid=None, storage=None, indexdir=None):
		self.ntiid = ntiid if ntiid else indexname
		self.storage = storage if storage else DirectoryStorage(indexdir)
		self._book = (Book(), self.storage.get_index(indexname) )

	@property
	def book(self):
		return self._book[0]

	@property
	def bookidx(self):
		return self._book[1]

	@property
	def indexid(self):
		return self.get_ntiid()

	@property
	def indexname(self):
		return self.get_indexname()

	def get_ntiid(self):
		return self.ntiid

	def get_indexname(self):
		return self.bookidx.indexname

	def __str__( self ):
		return self.indexname

	def __repr__( self ):
		return '%s(indexname=%s)' % (self.__class__.__name__, self.indexname)

	@metric
	def search(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		with _BoundingProxy(self.bookidx.searcher(weighting=CSM)) as s:
			results = self.book.search(s, query)
		return results

	def suggest_and_search(self, query, *args, **kwargs):
		query = QueryObject.create(query, **kwargs)
		with _BoundingProxy(self.bookidx.searcher(weighting=CSM)) as s:
			results = self.book.suggest_and_search(s, query)
		return results

	def suggest(self, term, *args, **kwargs):
		query = QueryObject.create(term, **kwargs)
		with _BoundingProxy(self.bookidx.searcher(weighting=CSM)) as s:
			results = self.book.suggest(s, query)
		return results

	def close(self):
		self.bookidx.close()

def wbm_factory(*args, **kwargs):
	def f(indexname, *fargs, **fkwargs):
		ntiid = fkwargs.get('ntiid', None)
		indexdir = fkwargs.get('indexdir', None)
		if indexdir and index.exists_in(indexdir, indexname=indexname):
			storage = DirectoryStorage(indexdir)
			return WhooshBookIndexManager(indexname=indexname, ntiid=ntiid, storage=storage)
		else:
			return None
	return f
