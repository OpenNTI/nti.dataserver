from zope import interface

class ISearcher(interface.Interface):
	
	def search(query, limit=None, search_on=None):
		"""
		search the content using the specified query
		
		:param query: Search query
		:param limit: max number of search hits
		:param search_on: type items to search
		"""

	def suggest(term, limit=None, prefix=None, search_on=None, **kwargs):
		"""
		perform a word suggestion
		
		:param term: Search query
		:param limit: max number of search hits
		:param prefix: number of chars in terms for prefix
		:param search_on: type items to search
		"""
		
	def suggest_and_search(query, limit=None, search_on=None):
		"""
		do a word suggestion and perform a search
		
		:param term: Search query
		:param limit: max number of search hits
		:param search_on: type items to search
		"""
	
# -----------------------------

class IBookIndexManager(ISearcher):
	pass
	
# -----------------------------

class IUserIndexManager(ISearcher):
	
	def get_username():
		"""
		return the user for this manager
		"""
		
	def index_content(data, type_name=None):
		"""
		index the specified content
		
		:param data: data to index
		:param type_name: data type
		"""
		
	def update_content(data, type_name=None):
		"""
		update the specified content index
		
		:param data: data to index
		:param type_name: data type
		"""

	def delete_content(data, type_name=None):
		"""
		delete from the index the specified content
		
		:param data: data to delete
		:param type_name: data type
		"""
		
	def remove_index(type_name):
		"""
		remove the specified index
		
		:param type_name: index type
		"""
	
# -----------------------------
	
class IIndexManager(interface.Interface):
	pass

# -----------------------------
	
class IIndexableContent(interface.Interface):

	def get_schema():
		"""
		return the [whoosh] schema associated with this content
		"""

	def index_content(writer, externalValue, auto_commit=True, **commit_args):
		"""
		index the specified external value content using the specified writer

		:param writer: [whoosh] index writer
		:param externalValue: Object [dict] to index
		:param auto_commit: flag to save the content after it has been written in the index
		:param commit_args: [whoosh] index writer commit arguments
		"""

	def update_content(writer, externalValue, auto_commit=True, **commit_args):
		"""
		Update the index content for the specified external value content using the specified writer

		:param writer: [whoosh] index writer
		:param externalValue: Object [dict] to index
		:param auto_commit: flag to save the content after it has been written in the index
		:param commit_args: [whoosh] index writer commit arguments
		"""

	def delete_content(writer, externalValue, auto_commit=True, **commit_args):
		"""
		Delete the index entry for the specified external value content using the specified writer

		:param writer: [whoosh] index writer
		:param externalValue: Object to delete in index
		:param auto_commit: flag to save the content after it has been written in the index
		:param commit_args: [whoosh] index writer commit arguments
		"""

	############################

	def search(searcher, query, limit=None, sortedby=None, search_field=None):
		"""
		Search the index using the specified searcher

		:param searcher: [whoosh] index searcher
		:param query: Query string
		:param limit: Max number of items to return in the search
		:param search_field: search index field in the schema
		"""

	def quick_search(searcher, query, limit=None, sortedby=None, search_field=None):
		"""
		Perform a quick search (e.g iTunes) over the index using the specified searcher

		:param searcher: [whoosh] index searcher
		:param query: Query string
		:param limit: Max number of items to return in the search
		:param search_field: Search index field in the schema
		"""

	def suggest_and_search(searcher, query, limit=None, sortedby=None, search_field=None):
		"""
		Perform a suggest and search (e.g iTunes) over the index using the specified searcher

		:param searcher: [whoosh] index searcher
		:param query: Query string
		:param limit: Max number of items to return in the search
		:param search_field: Search index field in the schema
		"""

	def suggest(searcher, word, limit=None, maxdist=None, prefix=None, search_field=None):
		"""
		Perform a suggestion search over the index using the specified searcher

		:param searcher: [whoosh] index searcher
		:param word: suggestion word
		:param limit: Max number of items to return in the search
		:param maxdist: The largest edit distance from the given word to look at.
		:param prefix: Require suggestions to share a prefix of this length with the given word.
		:param search_field: Search index field in the schema
		"""

class IUserIndexableContent(IIndexableContent):

	def get_index_data(externalValue, *args, **kwargs):
		"""
		Return a dictionary with the data fields to set in the index

		:param externalValue: Object to gather the index data from
		:param args: non-keyworded argument list
		:param kwargs: keyworded variable arguments
		"""
