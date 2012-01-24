import logging
logger = logging.getLogger( __name__ )


from contenttypes import Book
from indexstorage import create_directory_index_storage


from zope import interface
from . import interfaces
from . import IndexTypeMixin

class BookIndexManager(object):
	interface.implements( interfaces.IBookIndexManager )
	def __init__(self, indexdir="/tmp/", indexname="prealgebra"):
		self.indexdir = indexdir
		self._book = IndexTypeMixin(Book(), create_directory_index_storage(indexdir).get_index(indexname) )

	@property
	def book(self):
		return self._book.instance

	@property
	def bookidx(self):
		return self._book.index

	@property
	def indexname(self):
		return self.bookidx.indexname

	##########################

	def search(self, query, limit=None):
		with self.bookidx.searcher() as s:
			results = self.book.search(s, query, limit)
		return results

	def quick_search(self, query, limit=None):
		with self.bookidx.searcher() as s:
			results = self.book.quick_search(s, query, limit)
		return results

	def suggest_and_search(self, query, limit=None):
		with self.bookidx.searcher() as s:
			results = self.book.suggest_and_search(s, query, limit)
		return results

	def suggest(self, word, limit=None, maxdist=None, prefix=None):
		with self.bookidx.searcher() as s:
			results = self.book.suggest(s, word, limit=limit, maxdist=maxdist, prefix=prefix)
		return results

	##########################

	def close(self):
		self.bookidx.close()

	def __del__(self):
		try:
			self.close()
		except:
			pass


