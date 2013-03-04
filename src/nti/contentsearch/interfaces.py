# -*- coding: utf-8 -*-
"""
Search interfaces.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import

from zope import schema
from zope import interface
from zope import component
from zope.deprecation import deprecated
from zope.index import interfaces as zidx_interfaces
from zope.interface.common.sequence import IMinimalSequence
from zope.interface.common.mapping import IReadMapping, IMapping, IFullMapping

from repoze.catalog import interfaces as rcat_interfaces

from dolmen.builtins import IDict

from nti.dataserver import interfaces as nti_interfaces
from nti.externalization import interfaces as ext_interfaces

from nti.utils.schema import IndexedIterable as TypedIterable

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

class IWooshBookIndexManager(IBookIndexManager):

	def close():
		"close the index"

class IEntityIndexManager(ISearcher):

	username = schema.TextLine(title="entity name", required=True)

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

class IIndexEvent(component.interfaces.IObjectEvent):
	data = schema.Object(nti_interfaces.IModeledContent, title="The indexed object")
	user = schema.Object(nti_interfaces.IEntity, title="The entity that indexed the object")

class IObjectIndexed(IIndexEvent):
	pass

class IObjectReIndexed(IIndexEvent):
	pass

class IObjectUnIndexed(IIndexEvent):
	pass

class IndexEvent(component.interfaces.ObjectEvent):
	def __init__( self, data, user ):
		super(IndexEvent,self).__init__( data )
		self.user = user

@interface.implementer(IObjectIndexed)
class ObjectIndexedEvent(IndexEvent):
	pass

@interface.implementer(IObjectReIndexed)
class ObjectReIndexedEvent(IndexEvent):
	pass

@interface.implementer(IObjectUnIndexed)
class ObjectUnIndexedEvent(IndexEvent):
	pass
		
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

class IBookContent(interface.Interface):
	docnum = schema.Int(title="Document number", required=True)
	ntiid = schema.Float(title="NTIID", required=True)
	title = schema.Text(title="Content title", required=True)
	content = schema.Text(title="Text content", required=True)
	last_modified = schema.Float(title="Last modified date", required=True)

class IWhooshBookContent(IBookContent, IReadMapping):
	intid = schema.Int(title="Alias for docnum", required=True)
	score = schema.Float(title="Search score", required=False, default=1.0)


class IBookSchemaCreator(interface.Interface):
	pass

class IWhooshBookSchemaCreator(IBookSchemaCreator):
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

class INTIIDResolver(interface.Interface):

	def get_ntiid():
		"""return the NTI identifier"""

class IContainerIDResolver(interface.Interface):

	def get_containerId():
		"""return the container identifier"""

class ILastModifiedResolver(interface.Interface):

	def get_last_modified():
		"""return the last modified date"""

class ICreatorResolver(interface.Interface):

	def get_creator():
		"""return the creator"""

class IShareableContentResolver(interface.Interface):

	def get_sharedWith():
		"""return the share with users"""
		
class _ContentMixinResolver(IContentResolver,
							INTIIDResolver,
							IContainerIDResolver,
							ILastModifiedResolver):
	pass

class IUserContentResolver(_ContentMixinResolver, ICreatorResolver):
	pass
		
class IThreadableContentResolver(IUserContentResolver, IShareableContentResolver):

	def get_keywords():
		"""return the key words"""

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

class IPostContentResolver(_ContentMixinResolver,
						   ICreatorResolver,
						   IShareableContentResolver):

	def get_title():
		"""return the post/forum title"""
		
	def get_tags():
		"""return the post/forum tags"""
		
class IBookContentResolver(_ContentMixinResolver):
	pass

class IModeledContentResolver(IPostContentResolver,
							  IMessageInfoContentResolver,
							  IRedactionContentResolver, 
							  IHighlightContentResolver,
							  INoteContentResolver):
	pass

# content processing

class IStopWords(interface.Interface):

	def stopwords(language):
		"""return stop word for the specified language"""

	def available_languages():
		"available languages"

# Catalog creators marker interfaces

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

class IPostRepozeCatalogFieldCreator(interface.Interface):
	pass

# redis

class IRedisStoreService(interface.Interface):
	queue_name = schema.TextLine(title="Queue name", required=True)
	sleep_wait_time = schema.Float(title="Message interval", required=True)
	expiration_time = schema.Float(title="Message redis expiration time", required=True)

	def add(docid, username):
		"""
		register an add index operation with redis

		:param docid document id
		:param username target user
		"""

	def update(docid, username):
		"""
		register a update index operation with redis

		:param docid document id
		:param username target user
		"""

	def delete(docid, username):
		"""
		register a delete index operation with redis

		:param docid document id
		:param username target user
		"""

	def process_messages(msgs):
		"""
		process the messages read from redis
		"""

# cloud search

class ICloudSearchObject(IDict):
	pass

class ICloudSearchStore(interface.Interface):

	def get_domain(domain_name=None):
		"""
		Return the domain with the specified name
		"""

	def get_document_service(domain_name=None):
		"""
		Return a document service for the specified domain
		"""

	def get_search_service(domain_name=None):
		"""
		Return the searchh service for the specified domain
		"""

	def get_aws_domains():
		"""
		Return all aws search domains
		"""
		
	def search(*args, **kwargs):
		"""
		Perform a CloudSearch search
		"""
	
	def add(docid, username, service=None, commit=True):
		"""
		Index the specified document in CloudSearch
		"""
			
	def delete(docid, username, ommit=True):
		"""
		Delete the specified document from CloudSearch
		"""
		
	def handle_cs_errors(errors):
		"""
		Handle the specififed CloudSearch error meessages
		"""

class ICloudSearchStoreService(IRedisStoreService):
	store = schema.Object(ICloudSearchStore, title='CloudSearch store')

class ICloudSearchQueryParser(interface.Interface):

	def parse(qo):
		"""parse the specified ISearchQuery query object"""

# search query

class ISearchQuery(interface.Interface):
	term = schema.TextLine(title="Query search term", required=True)
	username = schema.TextLine(title="User doing the search", required=True)

	limit = schema.Int(title="search results limit", required=False)
	indexid = schema.TextLine(title="Book content NTIID", required=False)
	searchOn = schema.Set(value_type=schema.TextLine(title='The ntiid'), title="Content types to search on", required=False)
	sortOn = schema.TextLine(title="Field or function to sort by", required=False)
	location = schema.TextLine(title="The reference NTIID where the search was invoked", required=False)
	sortOrder = schema.TextLine(title="descending or ascending  to sort order", default='descending', required=False)

	batchSize = schema.Int(title="page size", required=False)
	batchStart = schema.Int(title="The index of the first object to return, starting with zero", required=False)

	is_prefix_search = schema.Bool(title="Returns true if the search is for prefix search", required=True, readonly=True)
	is_phrase_search = schema.Bool(title="Returns true if the search is for phrase search", required=True, readonly=True)
	is_descending_sort_order = schema.Bool(title="Returns true if the sortOrder is descending", required=True, default=True, readonly=True)

class ISearchQueryValidator(interface.Interface):

	def validate(query):
		"""check if the specified search query is valid"""

class IRepozeSearchQueryValidator(ISearchQueryValidator):
	pass

# search results

class IBaseHit(interface.Interface):
	"""represent a base search hit"""
	query = interface.Attribute("The query that produced this hit")
	score = schema.Float(title="hit relevance score", required=True, readonly=True)

class IIndexHit(IBaseHit, IMinimalSequence):
	"""represent a search hit stored in a ISearchResults"""
	obj = interface.Attribute("The hit object")

class ISearchHit(IBaseHit, IMapping, ext_interfaces.IExternalObject):
	"""represent an externalized search hit"""
	oid = interface.Attribute("hit unique id")
	last_modified = schema.Float(title="last modified date for this hit", required=False, readonly=True)

class ISearchHitComparator(interface.Interface):
	def compare(a, b):
		"""Compare arguments for for order. a or b can beither a IndexHit or ISearchHit"""

class IIndexHitMetaDataTracker(interface.Interface):
	"""Class to track index hit meta data"""

	def track(ihit):
		"""track any metadata from the specified index hit"""

	def __iadd__(other):
		pass

class IBaseSearchResults(interface.Interface):
	query = interface.Attribute("Search query")

class ISearchResults(IBaseSearchResults):
	hits = TypedIterable( value_type=schema.Object(IIndexHit, title="index hit"),
						  title="IIndexHit objects", required=True, readonly=True)

	def add(hit_or_hits):
		"""add a search hit(s) to this result"""

	def sort():
		"""sort the results based on the sortBy query param"""

	def __iadd__(other):
		pass

class ISuggestResults(IBaseSearchResults):
	
	suggestions = TypedIterable(
		title="suggested words",
		description="Order may or may not be significant",
		required=True,
		readonly=True,
		value_type=schema.TextLine(title="suggested word") )

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

