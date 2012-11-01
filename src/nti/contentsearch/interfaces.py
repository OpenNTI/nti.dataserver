from __future__ import print_function, unicode_literals

from zope import schema
from zope import interface
from zope import component
from zope.deprecation import deprecated
from zope.index import interfaces as zidx_interfaces
from zope.interface.common.mapping import IFullMapping

from repoze.catalog import interfaces as rcat_interfaces

from dolmen.builtins import IDict

from nti.utils.property import alias
from nti.dataserver import interfaces as nti_interfaces
from nti.externalization import interfaces as ext_interfaces

deprecated( 'IRepozeDataStore', 'Use lastest index implementation' )
class IRepozeDataStore(IFullMapping):
	
	def has_user(username):
		"""
		return if the store has catalogs for the specified user
		
		:param user: username
		"""
		
# searcher
	
class ISearcher(interface.Interface):
	
	def search(query):
		"""
		search the content using the specified query
		
		:param query: Search query
		"""
		
	def suggest(query):
		"""
		perform a word suggestion
		
		:param query: Search query
		"""
		
	def suggest_and_search(query):
		"""
		do a word suggestion and perform a search
		
		:param query: Search query
		"""
	
class ISearchFeatures(interface.Interface):
	is_ngram_search_supported = schema.Bool(title="Property for ngram search support.", default=False, readonly=True)
	is_word_suggest_supported = schema.Bool(title="Property for word suggestion support.", default=False, readonly=True)
	
class IBookIndexManager(ISearcher):
	
	def get_indexname():
		"return the index name"
		
	def get_ntiid():
		"return the index ntiid"
	
class IEntityIndexManager(ISearcher):

	username = schema.TextLine(title="entity name", required=True)
	
	def has_stored_indices():
		"""
		return if there are accessible/stored indices for the user
		"""
		
	def get_stored_indices():
		"""
		return the index names accessible/stored in this manager for the user
		"""
				
	def index_content(data, type_name=None):
		"""
		index the specified content
		
		:param data: data to index
		:param type_name: data type
		:return whether the data as indexed successfully
		"""
		
	def update_content(data, type_name=None):
		"""
		update the specified content index
		
		:param data: data to index
		:param type_name: data type
		:return whether the data as reindexed successfully
		"""

	def delete_content(data, type_name=None):
		"""
		delete from the index the specified content
		
		:param data: data to delete
		:param type_name: data type
		:return whether the data as deleted from the index successfully
		"""
		
	def remove_index(type_name):
		"""
		remove the specified index
		
		:param type_name: index type
		"""
	
# index events

IE_INDEXED   = "Indexed"
IE_REINDEXED = "Reindexed"
IE_UNINDEXED = "Unindexed"

class IIndexEvent(component.interfaces.IObjectEvent):
	"""
	An index event
	"""
	target = schema.Object(nti_interfaces.IEntity,
						   title="The entity in the index event")
	
	data = schema.Object(nti_interfaces.IModeledContent,
						 title="The object in the index event")
	
	event_type = schema.Choice(values=(IE_INDEXED, IE_REINDEXED, IE_UNINDEXED),
							   title="Index event type")


@interface.implementer(IIndexEvent)
class IndexEvent(component.interfaces.ObjectEvent):

	def __init__( self, user, data, event_type ):
		super(IndexEvent,self).__init__( user )
		self.data = data
		self.event_type = event_type
	target = alias('object')

# entity adapters

class IRepozeEntityIndexManager(IEntityIndexManager):
	pass

class IWhooshEntityIndexManager(IEntityIndexManager):
	pass

class ICloudSearchEntityIndexManager(IEntityIndexManager):
	pass

# index manager
	
class IIndexManager(interface.Interface):
	
	def search(query):
		"""
		perform a search query
		
		:param query: query object
		"""
		
	def suggest_and_search(query):
		"""
		perform a  word suggestion and search
		
		:param query: query object
		"""
	
	def suggest(query):
		"""
		perform a word suggestion search
		
		:param query: query object
		"""
		
	def content_search(query):
		"""
		perform a book search
		
		:param query: search query
		"""

	def content_suggest_and_search(query):
		"""
		perform a book word suggestion and search
		
		:param query: Search query
		"""
		
	def content_suggest(query):
		"""
		perform a book word suggestion
		
		:param query: Word fragment
		"""
	
	def user_data_search(query):
		"""
		perform a user data content search
		
		:param query: search query
		"""

	def user_data_suggest_and_search(query):
		"""
		perform a book user data suggestion and search
		
		:param query: Search query
		"""

	def user_data_suggest(query):
		"""
		perform a user data word suggestion
		
		:param word: Word fragment
		"""
		
	def index_user_content(username, data, type_name=None):
		"""
		index the specified content
		
		:param username: content owner
		:param data: data to index
		:param type_name: data type
		"""

	def update_user_content(username, data, type_name=None):
		"""
		update the index for specified content
		
		:param username: content owner
		:param data: data to index
		:param type_name: data type
		"""

	def delete_user_content(username, data, type_name=None):
		"""
		delete from the index the specified content
		
		:param username: content owner
		:param data: data to remove from index
		:param type_name: data type
		"""
	
# zopyx storage

class ITextIndexNG3(zidx_interfaces.IInjection, zidx_interfaces.IIndexSearch, zidx_interfaces.IStatistics):
	def suggest(term, threshold, prefix):
		"""
		return a list of similar words based on the levenshtein distance
		"""
		
	def getLexicon():
		"""
		return the zopyx.txng3.core.interfaces.ILexicon for this text index
		"""
	
	def setLexicon(lexicon):
		"""
		set the zopyx.txng3.core.interfaces.ILexicon for this text index
		"""

class ICatalogTextIndexNG3(rcat_interfaces.ICatalogIndex, zidx_interfaces.IIndexSort, ITextIndexNG3):
	pass

# whoosh index storage

class IWhooshIndexStorage(interface.Interface):

	def create_index(indexname, schema):
		"""
		create the an index with the specified index an schema
				
		:param indexname: index name
		:param schema: whoosh schema
		"""	
	
	def index_exists(indexname):
		"""
		check if the specified index exists
				
		:param indexname: index name
		"""	
	
	def get_index(indexname):
		"""
		return the whoosh index with the specified index name
				
		:param indexname: index name
		"""	
	
	def get_or_create_index(indexname, schema=None, recreate=True):
		"""
		get or create the index the specified index name
				
		:param indexname: index name
		:param schema: whoosh schema
		"""	
	
	def open_index(indexname, schema=None):
		"""
		open the index with the specified name
				
		:param indexname: index name
		:param schema: whoosh schema
		"""	
	
	def storage():
		"""
		return a index underlying [file] data storage
		"""	
	
	def ctor_args():
		"""
		return a dictionary with the arguments to be passed to an index writer constructor
		""" 
	
	def commit_args():
		"""
		return a dictionary with the arguments to be passed to an index writer commit method
		""" 

# book content

class IWhooshBookContent(interface.Interface):
	pass

# text highlight types

class IHighlightType(interface.Interface):
	pass

class INoSnippetHighlight(IHighlightType):
	pass

class IWordSnippetHighlight(IHighlightType):
	pass

# user generated content resolvers

class IContentResolver(interface.Interface):
	
	def get_content():
		"""return the text content to index"""
		
class IUserContentResolver(IContentResolver):
		
	def get_ntiid():
		"""return the NTI identifier"""
		
	def get_external_oid():
		"""return the external object identifier"""
	
	def get_creator():
		"""return the creator"""
	
	def get_containerId():
		"""return the container identifier"""
	
	def get_last_modified():
		"""return the last modified"""
	
class IThreadableContentResolver(IUserContentResolver):
	
	def get_keywords():
		"""return the key words"""
	
	def get_sharedWith():
		"""return the share with users"""
	
	def get_inReplyTo():
		"""return the inReplyTo nttid"""
		
class IHighlightContentResolver(IThreadableContentResolver):
	pass
	
class IRedactionContentResolver(IHighlightContentResolver):
	
	def get_replacement_content():
		"""return the replacement content"""
		
	def get_redaction_explanation():
		"""return the redaction explanation content"""
	
class INoteContentResolver(IHighlightContentResolver):
	
	def get_references():
		"""return the nttids of the objects its refers"""
	
class IMessageInfoContentResolver(IThreadableContentResolver):
	
	def get_id():
		"""return the message id"""
		
	def get_channel():
		"""return the message channel"""
		
	def get_recipients():
		"""return the message recipients"""

# content processing

class IContentTranslationTable(interface.Interface):
	"""marker interface for content translationt table"""
	pass
		
class IContentTokenizer(interface.Interface):
	
	def tokenize(data):
		"""tokenize the specifeid text data"""
		
class IContentTokenizer(interface.Interface):
	
	def tokenize(data):
		"""tokenize the specifeid text data"""
	
class IStopWords(interface.Interface):

	def stopwords(language):
		"""return stop word for the specified language"""
		
	def available_languages():
		"available languages"
		
class INgramComputer(interface.Interface):
	minsize = schema.Int(title="min ngram size", required=True)
	minsize = schema.Int(title="max ngram size", required=True)
	
	def compute(text):
		"""compute the ngrams for the specified text"""
		
# Catalog creators
	
class IRepozeCatalogCreator(interface.Interface):
	pass

class IRepozeCatalogFieldCreator(interface.Interface):
	pass

class INoteRepozeCatalogFieldCreator(interface.Interface):
	pass

class IHighlightRepozeCatalogFieldCreator(interface.Interface):
	pass

class IRedactionRepozeCatalogFieldCreator(interface.Interface):
	pass

class IMessageInfoRepozeCatalogFieldCreator(interface.Interface):
	pass

# cloud search

class ICloudSearchObject(IDict):
	pass
	
class ICloudSearchStore(interface.Interface):
	
	def get_domain(domain_name):
		"""return the domain with the specified domain"""
	
	def get_document_service(domain_name):
		"""return a document service for the specified domain"""
	
	def get_search_service(domain_name):
		"""return the searchh service for the specified domain"""
	
	def get_aws_domains():
		"""return all aws search domains"""
		
class ICloudSearchStoreService(interface.Interface):
	
	# document service
	
	def add(_id, version, fields):
		"""
		index the specified data fields
		
		:param _id cloud search document id
		:param version document version
		:param fields : data-dict to index
		"""
	
	def delete(_id, version):
		"""
		unindex the specified document
		
		:param _id cloud search document id
		:param version document version
		"""
	
	def commit():
		"""
		commit index operation(s)
		"""
	
	# search service
	
	def search( *args, **kwargs):
		"""
		return a searh against cloud search
		"""
		
class ICloudSearchQueryParser(interface.Interface):
	
	def parse(qo):
		"""parse the specified ISearchQuery query object"""
		
# search query

class ISearchQuery(interface.Interface):
	term = schema.TextLine(title="Query search term", required=True)
	username = schema.TextLine(title="User doing the search", required=True)
	limit = schema.Int(title="search results limit", required=False)
	indexid = schema.TextLine(title="Book content NTIID", required=False)
	searchon = schema.Iterable("Content types to search on", required=False)
	batchSize = schema.Int(title="page size", required=False)
	batchStart = schema.Int(title="The index of the first object to return, starting with zero", required=False)
	
	is_prefix_search = schema.Bool(title="Returns true if the search is for prefix search", required=True, readonly=True)
	is_phrase_search = schema.Bool(title="Returns true if the search is for phrase search", required=True, readonly=True)
		
class ISearchQueryValidator(interface.Interface):
	
	def validate(query):
		"""check if the specified search query is valid"""
		
class IRepozeSearchQueryValidator(ISearchQueryValidator):
	pass

# search results

class IWordSimilarity(interface.Interface):	
	def compute(a, b):
		"""compute a similarity ratio for the specified words"""
		
	def rank(word, terms, reverse=True):
		"""return the specified terms based on the distance to the specified word"""
		
class ISearchHit(ext_interfaces.IExternalObject):
	query = schema.TextLine(title="query that produced this hit")
	last_modified = schema.Float(title="last modified date for this hit")
	score = schema.Float(title="query relevance score")
	
class IBaseSearchResults(interface.Interface):
	query = schema.Object(ISearchQuery, title="search query")
	pass

class ISearchResults(IBaseSearchResults):
	hits = schema.Iterable("search result hits")
	
	def add(hit_or_hits):
		"""add a search hit(s) to this result"""
	
class ISuggestResults(IBaseSearchResults):
	suggestions = schema.Iterable("suggested words")
	
	def add_suggestions(word_or_words):
		"""add a word suggestion(s) to this result"""
	
	add = add_suggestions
	
class ISuggestAndSearchResults(ISearchResults, ISuggestResults):
	def add(hit_or_hits):
		"""add a search hit(s) to this result"""
		
class ISearchResultsCreator(interface.Interface):
	def __call__(query):
		"""return a new instance of a ISearchResults"""
	
class ISuggestResultsCreator(interface.Interface):
	def __call__(query):
		"""return a new instance of a ISuggestResults"""
		
class ISuggestAndSearchResultsCreator(interface.Interface):
	def __call__(query):
		"""return a new instance of a ISuggestAndSearchResults"""
