from zope import interface

from nti.contentsearch import interfaces
from nti.contentsearch._whoosh_index import Book
from nti.contentsearch._whoosh_indexstorage import create_directory_index_storage

import logging
logger = logging.getLogger( __name__ )

# ----------------------------------

class WhooshBookIndexManager(object):
	interface.implements( interfaces.IBookIndexManager )
	
	def __init__(self, indexname, *args, **kwargs):
		self.indexdir = kwargs.get('indexdir', None)
		self.storage = kwargs.get('storage', None) or kwargs.get('index_storage', None) 
		assert self.storage or self.indexdir, "must specified a index directory or an index storage"
		self.storage = self.storage or create_directory_index_storage(self.indexdir)
		self._book = (Book(), self.storage.get_index(indexname) )

	@property
	def book(self):
		return self._book[0]

	@property
	def bookidx(self):
		return self._book[1]

	@property
	def indexname(self):
		return self.get_indexname()

	def get_indexname(self):
		return self.bookidx.indexname
	
	def __str__( self ):
		return self.indexname

	def __repr__( self ):
		return 'WhooshBookIndexManager(indexname=%s)' % self.indexname
	
	# ---------------

	def search(self, query, limit=None, *args, **kwargs):
		with self.storage.dbTrans():
			with self.bookidx.searcher() as s:
				results = self.book.search(s, query, limit)
		return results

	def ngram_search(self, query, limit=None, *args, **kwarg):
		with self.bookidx.searcher() as s:
			results = self.book.ngram_search(s, query, limit)
		return results

	def suggest_and_search(self, query, limit=None, *args, **kwarg):
		with self.storage.dbTrans():
			with self.bookidx.searcher() as s:
				results = self.book.suggest_and_search(s, query, limit)
		return results

	def suggest(self, term, limit=None, prefix=None, *args, **kwargs):
		with self.storage.dbTrans():
			maxdist = kwargs.get('maxdist', None)
			with self.bookidx.searcher() as s:
				results = self.book.suggest(s, term, limit=limit, maxdist=maxdist, prefix=prefix)
		return results

	quick_search = ngram_search
	
	# ---------------

	def close(self):
		self.bookidx.close()

	def __del__(self):
		try:
			self.close()
		except:
			pass

# -----------------------------

def wbm_factory(*args, **kwargs):
	def f(indexname, *fargs, **fkwargs):
		return WhooshBookIndexManager(indexname=indexname, **fkwargs)
	return f
