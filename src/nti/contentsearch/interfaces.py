from __future__ import print_function, unicode_literals

from zope import interface
from zope.interface.common.mapping import IFullMapping

from nti.externalization import interfaces as ext_interfaces

# -----------------------------

class IRepozeDataStore(IFullMapping):
	def has_user(username):
		"""
		return if the store has catalogs for the specified user
		
		:param user: username
		"""

# -----------------------------

class ICloudSearchStore(interface.Interface):
	def get_connection():
		"""
		return the cloud store connection
		"""
	
	def get_domain(domain_name):
		"""
		return the cloud search domain with the specifeid name
		"""
		

# -----------------------------

class ISearcher(interface.Interface):
	
	def search(query, *args, **kwargs):
		"""
		search the content using the specified query
		
		:param query: Search query
		:param limit: max number of search hits
		:param search_on: type items to search
		"""
	
	def ngram_search(query, *args, **kwargs):
		"""
		search the content using ngram for the specified query
		
		:param query: Search query
		:param limit: max number of search hits
		:param search_on: type items to search
		"""
		
	def suggest(query, *args, **kwargs):
		"""
		perform a word suggestion
		
		:param query: Search query
		:param limit: max number of search hits
		:param prefix: number of chars in terms for prefix
		:param search_on: type items to search
		"""
		
	def suggest_and_search(query, *args, **kwargs):
		"""
		do a word suggestion and perform a search
		
		:param term: Search query
		:param limit: max number of search hits
		:param search_on: type items to search
		"""
	
# -----------------------------

class IBookIndexManager(ISearcher):
	def get_indexname(self):
		return self.bookidx.indexname
	
# -----------------------------

class IUserIndexManager(ISearcher):
	
		
	def get_username():
		"""
		return the user for this manager
		"""

	def has_stored_indices():
		"""
		return if there are accessible/stored indices for the user
		"""
		
	def get_stored_indices():
		"""
		return the index names accessible/stored in this manager for the user
		"""
				
	def index_content(data, type_name=None, *args, **kwargs):
		"""
		index the specified content
		
		:param data: data to index
		:param type_name: data type
		"""
		
	def update_content(data, type_name=None, *args, **kwargs):
		"""
		update the specified content index
		
		:param data: data to index
		:param type_name: data type
		"""

	def delete_content(data, type_name=None, *args, **kwargs):
		"""
		delete from the index the specified content
		
		:param data: data to delete
		:param type_name: data type
		"""
		
	def remove_index(type_name, *args, **kwargs):
		"""
		remove the specified index
		
		:param type_name: index type
		"""
	
# -----------------------------

class IUserIndexManagerFactory(interface.Interface):
	def __call__(username, *args, **kwargs):
		"""
		return a user index manager for the specified user
		"""
		
# -----------------------------
	
class IIndexManager(interface.Interface):
	
	def search(query, *args, **kwargs):
		"""
		perform a search query
		
		:param query: query object
		"""
		
	def ngram_search(query, *args, **kwargs):
		"""
		perform a ngram based search
		
		:param query: query object
		"""
		
	def suggest_and_search(query, *args, **kwargs):
		"""
		perform a  word suggestion and search
		
		:param query: query object
		"""
	
	def suggest(query, *args, **kwargs):
		"""
		perform a word suggestion search
		
		:param query: query object
		"""
		
	def content_search(query,  *args, **kwargs):
		"""
		perform a book search
		
		:param indexname: book index name
		:param query: search query
		:param limit: max number of search hits
		"""
	
	def content_ngram_search(query, *args, **kwargs):
		"""
		perform a ngram based content search
		
		:param indexname: book index name
		:param query: Search query
		:param limit: max number of search hits
		"""
		
	def content_suggest_and_search(query, *args, **kwargs):
		"""
		perform a book word suggestion and search
		
		:param indexname: book index name
		:param query: Search query
		:param limit: max number of search hits
		"""
		
	def content_suggest(query, *args, **kwargs):
		"""
		perform a book word suggestion
		
		:param indexname: book index name
		:param word: Word fragment
		:param limit: max number of search hits
		:param prefix: number of chars in terms for prefix
		"""
	
	def user_data_search(query, limit=None, *args, **kwargs):
		"""
		perform a user data content search
		
		:param username: user name
		:param query: search query
		:param limit: max number of search hits
		"""

	def user_data_ngram_search(query, *args, **kwargs):
		"""
		perform a user data ngram based content search
		
		:param username: user name
		:param query: search query
		:param limit: max number of search hits
		"""

	def user_data_suggest_and_search(query, *args, **kwargs):
		"""
		perform a book user data suggestion and search
		
		:param username: user name
		:param query: Search query
		:param limit: max number of search hits
		"""

	def user_data_suggest(query, *args, **kwargs):
		"""
		perform a user data word suggestion
		
		:param username: user name
		:param word: Word fragment
		:param limit: max number of search hits
		:param prefix: number of chars in terms for prefix
		"""
		
	def index_user_content(username, data, type_name=None, *args, **kwargs):
		"""
		index the specified content
		
		:param username: content owner
		:param data: data to index
		:param type_name: data type
		"""

	def update_user_content(username, data, type_name=None, *args, **kwargs):
		"""
		update the index for specified content
		
		:param username: content owner
		:param data: data to index
		:param type_name: data type
		"""

	def delete_user_content(username, data, type_name=None, *args, **kwargs):
		"""
		delete from the index the specified content
		
		:param username: content owner
		:param data: data to remove from index
		:param type_name: data type
		"""

# -----------------------------
	
class IWhooshIndexStorage(interface.Interface):

	def create_index(indexname, schema, **kwargs):
		"""
		create the an index with the specified index an schema
				
		:param indexname: index name
		:param schema: whoosh schema
		"""	
	
	def index_exists(indexname, **kwargs):
		"""
		check if the specified index exists
				
		:param indexname: index name
		"""	
	
	def get_index(indexname, **kwargs):
		"""
		return the whoosh index with the specified index name
				
		:param indexname: index name
		"""	
	
	def get_or_create_index(indexname, schema=None, recreate=True, **kwargs):
		"""
		get or create the index the specified index name
				
		:param indexname: index name
		:param schema: whoosh schema
		"""	
	
	def open_index(indexname, schema=None, **kwargs):
		"""
		open the index with the specified name
				
		:param indexname: index name
		:param schema: whoosh schema
		"""	
	
	def dbTrans():
		"""
		return a context manager (db/io transaction) to perform an index operation
		"""	
	
	def storage(**kwargs):
		"""
		return a index underlying [file] data storage
		"""	
	
	def ctor_args(**kwargs):
		"""
		return a dictionary with the arguments to be passed to an index writer constructor
		""" 
	
	def commit_args(**kwargs):
		"""
		return a dictionary with the arguments to be passed to an index writer commit method
		""" 

# -----------------------------

class IHighlightType(interface.Interface):
	pass

class INoSnippetHighlight(IHighlightType):
	pass

class IWordSnippetHighlight(IHighlightType):
	pass

class INgramSnippetHighlight(IHighlightType):
	pass

class ISearchHit(ext_interfaces.IExternalObject):
	query = interface.Attribute("""query that produced this hit""")
	pass
