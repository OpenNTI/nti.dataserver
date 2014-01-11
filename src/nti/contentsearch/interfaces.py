# -*- coding: utf-8 -*-
"""
Search interfaces.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

import sys

from zope import schema
from zope import component
from zope import interface
from zope.deprecation import deprecated
from zope.mimetype import interfaces as zmime_interfaces
from zope.interface.common.mapping import IMapping, IFullMapping

from nti.dataserver import interfaces as nti_interfaces

from . import constants

from nti.utils import schema as nti_schema

deprecated('IRepozeDataStore', 'Use lastest index implementation')
class IRepozeDataStore(IFullMapping):
	"""
	This interface is implemented by persistent objects in databases
	in the wild (notably, these objects were registered as persistent utilities,
	so the persistent registry has a handle to this class).  Therefore, it MUST remain
	here as an interface (or we have to clean out the databases); otherwise add errors result such as this one::

	  zope.interface-4.0.5-py2.7-macosx-10.9-x86_64.egg/zope/interface/adapter.py", line 493, in add_extendor
         for i in provided.__iro__:
      AttributeError: type object 'IRepozeDataStore' has no attribute '__iro__'
	"""

# search query

SEARCH_TYPES_VOCABULARY = \
	schema.vocabulary.SimpleVocabulary(
				[schema.vocabulary.SimpleTerm(_x) \
				for _x in constants.indexable_type_names + (constants.invalid_type_,)])

class ISearchQuery(interface.Interface):

	term = nti_schema.ValidTextLine(title="Query search term", required=True)
	username = nti_schema.ValidTextLine(title="User doing the search", required=False)
	language = nti_schema.ValidTextLine(title="Query search term language", required=False,
										default='en')

	limit = schema.Int(title="search results limit", required=False, default=sys.maxint)

	indexid = nti_schema.ValidTextLine(title="Book content NTIID", required=False)

	searchOn = nti_schema.ListOrTuple(
						value_type=schema.Choice(vocabulary=SEARCH_TYPES_VOCABULARY),
						title="Content types to search on", required=False)

	sortOn = nti_schema.ValidTextLine(title="Field or function to sort by", required=False)

	location = nti_schema.ValidTextLine(title="The reference NTIID where the search was invoked",
										required=False)
	sortOrder = nti_schema.ValidTextLine(title="descending or ascending  to sort order",
										 default='descending', required=False)

	surround = schema.Int(title="Hightlight surround chars", required=False,
						  default=20, min=1)

	maxchars = schema.Int(title="Hightlight max chars", required=False,
						  default=300, min=1)

	prefix = schema.Int(title="Suggestion prefix", required=False, min=1)
	threshold = nti_schema.Number(title="Suggestion threshold", required=False,
								  default=0.4999, min=0.0)
	maxdist = schema.Int(title="Maximun edit distance from the given word to look at",
						 required=False, default=15, min=2)

	batchSize = schema.Int(title="page size", required=False)
	batchStart = schema.Int(title="The index of the first object to return, starting with zero",
						    required=False, min=0)

	IsEmpty = schema.Bool(title="Returns true if this is an empty search",
						   required=True, readonly=True)

	IsBatching = schema.Bool(title="Returns true if this is a batch search",
							 required=True, readonly=True)

	IsPrefixSearch = schema.Bool(title="Returns true if the search is for prefix search",
								 required=True, readonly=True)

	IsPhraseSearch = schema.Bool(title="Returns true if the search is for phrase search",
								 required=True, readonly=True)

	IsDescendingSortOrder = schema.Bool(title="Returns true if the sortOrder is descending",
								 		required=True, readonly=True)


class ISearchQueryValidator(interface.Interface):

	def validate(query):
		"""check if the specified search query is valid"""

class ISearchQueryParser(interface.Interface):

	def parse(query):
		"""parse the specified query"""

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

class IContentSearcher(ISearcher):
	indices = interface.Attribute("index names")

class IWhooshContentSearcher(IContentSearcher):

	def get_index(indexname):
		"""
		return the whoosh index w/ the specified name
		"""

	def close():
		"""
		close all indices
		"""

class IContentSearcherFactory(interface.Interface):

	def __call__(*args, **kwargs):
		"""
		return an instance of a IContentSearcher
		"""

class IWhooshContentSearcherFactory(IContentSearcherFactory):

	def __call__(indexname, ntiid=None, **kwargs):
		"""
		return an instance of a IWhooshContentSearcher
		"""

class IEntityIndexController(ISearcher):

	def index_content(data):
		"""
		index the specified content

		:param data: data to index
		:param type_name: data type
		:return whether the data as indexed successfully
		"""

	def update_content(data):
		"""
		update the specified content index

		:param data: data to index
		:param type_name: data type
		:return whether the data as reindexed successfully
		"""

	def delete_content(data):
		"""
		delete from the index the specified content

		:param data: data to delete
		:param type_name: data type
		:return whether the data as deleted from the index successfully
		"""

	def unindex(oid):
		"""
		unindex the object with the specified id
		"""

class IEntityIndexManager(IEntityIndexController):

	username = nti_schema.ValidTextLine(title="entity name", required=True)

# entity adapters

class IRepozeEntityIndexManager(IEntityIndexManager):
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

	def index_user_content(user, data, type_name=None):
		"""
		index the specified content

		:param user: content owner
		:param data: data to index
		:param type_name: data type
		"""

	def update_user_content(user, data, type_name=None):
		"""
		update the index for specified content

		:param user: content owner
		:param data: data to index
		:param type_name: data type
		"""

	def delete_user_content(user, data, type_name=None):
		"""
		delete from the index the specified content

		:param username: content owner
		:param data: data to remove from index
		:param type_name: data type
		"""

	def unindex(user, oid):
		"""
		unindex the object with the specified id

		:param user: content owner
		:oid object id
		"""

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

class IRedisStoreService(interface.Interface):

	queue_name = nti_schema.ValidTextLine(title="Queue name", required=True)
	sleep_wait_time = nti_schema.Number(title="Message interval", required=True)
	expiration_time = nti_schema.Number(title="Message redis expiration time", required=True)

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

# content

class IWhooshContent(zmime_interfaces.IContentTypeAware):
	pass

class IBookContent(interface.Interface):
	ntiid = nti_schema.ValidTextLine(title="NTIID", required=True)
	title = nti_schema.ValidText(title="Content title", required=True)
	content = nti_schema.ValidText(title="Text content", required=True)
	last_modified = nti_schema.Number(title="Last modified date", required=True)

class IWhooshBookContent(IBookContent, IWhooshContent):
	docnum = schema.Int(title="Document number", required=True)
	score = nti_schema.Number(title="Search score", required=False, default=1.0)

class IVideoTranscriptContent(interface.Interface):
	containerId = nti_schema.ValidTextLine(title="NTIID of video container", required=True)
	videoId = nti_schema.ValidTextLine(title="Either the video NTIID or Id", required=True)
	content = nti_schema.ValidText(title="Text content", required=True)
	title = nti_schema.ValidText(title="Video title", required=False)
	start_millisecs = schema.Float(title="Start timestamp", required=True)
	end_millisecs = schema.Float(title="End timestamp", required=True)
	last_modified = nti_schema.Number(title="Last modified date", required=True)

class IWhooshVideoTranscriptContent(IVideoTranscriptContent, IWhooshContent):
	docnum = schema.Int(title="Document number", required=False)
	score = nti_schema.Number(title="Search score", required=False, default=1.0)

class INTICardContent(interface.Interface):
	href = nti_schema.ValidTextLine(title="card href", required=False)
	ntiid = nti_schema.ValidTextLine(title="card NTIID", required=True)
	title = nti_schema.ValidTextLine(title="Card title", required=True)
	creator = nti_schema.ValidTextLine(title="Card creator", required=True)
	last_modified = nti_schema.Number(title="Last modified date", required=True)
	description = nti_schema.ValidTextLine(title="Card description", required=True)
	target_ntiid = nti_schema.ValidTextLine(title="card target ntiid", required=False)
	containerId = nti_schema.ValidTextLine(title="card container ntiid", required=False)

class IWhooshNTICardContent(INTICardContent, IWhooshContent):
	docnum = schema.Int(title="Document number", required=False)
	score = nti_schema.Number(title="Search score", required=False, default=1.0)

class IContentSchemaCreator(interface.Interface):

	def create():
		"""
	 	create a content index schema
		"""

class IBookSchemaCreator(IContentSchemaCreator):
	pass

class IWhooshBookSchemaCreator(IBookSchemaCreator):
	pass

class IVideoTranscriptSchemaCreator(IContentSchemaCreator):
	pass

class IWhooshVideoTranscriptSchemaCreator(IVideoTranscriptSchemaCreator):
	pass

class INTICardSchemaCreator(IContentSchemaCreator):
	pass

class IWhooshNTICardSchemaCreator(INTICardSchemaCreator):
	pass

class IWhooshQueryParser(ISearchQueryParser):

	def parse(qo, schema=None):
		pass

# user generated content resolvers

class IContentResolver(interface.Interface):

	content = nti_schema.ValidTextLine(title="content to index", default=None)

class INTIIDResolver(interface.Interface):

	ntiid = nti_schema.ValidTextLine(title="NTIID identifier", default=None)

class IContainerIDResolver(interface.Interface):

	containerId = nti_schema.ValidTextLine(title="container identifier", default=None)

class ILastModifiedResolver(interface.Interface):

	lastModified = nti_schema.Float(title="last modified date", default=0.0)

class ICreatedTimeResolver(interface.Interface):

	createdTime = nti_schema.Float(title="created date", default=0.0)

class ICreatorResolver(interface.Interface):

	creator = nti_schema.ValidTextLine(title="creator user", default=None)

class ITitleResolver(interface.Interface):

	title = nti_schema.ValidTextLine(title="object title", default=None)

class ITagsResolver(interface.Interface):

	tags = nti_schema.ListOrTuple(nti_schema.ValidTextLine(title="tag"), title='tags',
								  default=())

class IKeywordsResolver(interface.Interface):

	keywords = nti_schema.ListOrTuple(nti_schema.ValidTextLine(title="keyword"),
									  title='keywords', default=())

class IShareableContentResolver(interface.Interface):

	sharedWith = nti_schema.ListOrTuple(nti_schema.ValidTextLine(title="username"),
									  	title='sharedWith', default=())


class _ContentMixinResolver(IContentResolver,
							INTIIDResolver,
							IContainerIDResolver,
							ILastModifiedResolver,
							ICreatedTimeResolver):
	pass

class IUserContentResolver(_ContentMixinResolver, ICreatorResolver):
	pass

class IThreadableContentResolver(IUserContentResolver,
								 ITagsResolver,
								 IKeywordsResolver,
								 IShareableContentResolver):

	inReplyTo = nti_schema.ValidTextLine(title="inReplyTo ntiid", default=None)

class IHighlightContentResolver(IThreadableContentResolver):
	pass

class IRedactionContentResolver(IHighlightContentResolver):

	replacementContent = nti_schema.ValidTextLine(title="replacement content",
												  default=None)

	redactionExplanation = nti_schema.ValidTextLine(title="replacement explanation",
													default=None)

class INoteContentResolver(IHighlightContentResolver, ITitleResolver):

	references = nti_schema.ListOrTuple(nti_schema.ValidTextLine(title="ntiid"),
									  	title='nttids references', default=())

class IMessageInfoContentResolver(IThreadableContentResolver):

	id = nti_schema.ValidTextLine(title="message id", default=None)

	channel = nti_schema.ValidTextLine(title="message channel", default=None)

	recipients = nti_schema.ListOrTuple(nti_schema.ValidTextLine(title="username"),
									  	title='message recipients', default=())

class IBlogContentResolver(_ContentMixinResolver,
							ICreatorResolver,
						  	IShareableContentResolver,
						  	ITitleResolver,
						  	ITagsResolver):

	id = nti_schema.ValidTextLine(title="post id", default=None)

class IPostContentResolver(IBlogContentResolver):
	pass

class IHeadlineTopicContentResolver(IBlogContentResolver):
	pass

class IBookContentResolver(_ContentMixinResolver):
	pass

class IVideoTranscriptContentResolver(_ContentMixinResolver):
	pass

class INTICardContentResolver(_ContentMixinResolver, ICreatorResolver):

	title = nti_schema.ValidTextLine(title="card title", default=None)

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

class IRepozeQueryParser(ISearchQueryParser):
	pass

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

class IRepozeSearchQueryValidator(ISearchQueryValidator):
	pass

# search results

class IBaseHit(interface.Interface):
	"""
	represent a base search hit
	"""
	Query = schema.Object(ISearchQuery, title="Search query", required=False)
	Score = nti_schema.Number(title="hit relevance score", required=True, default=1.0, min=0.0)

class IIndexHit(IBaseHit):
	"""
	represent a search hit stored in a ISearchResults
	"""
	Ref = nti_schema.Variant(
				(nti_schema.Object(nti_interfaces.IModeledContent,
								   description="A :class:`.IModeledContent`"),
				 nti_schema.Object(IWhooshContent, description="A :class:`.IWhooshContent`"),
				 nti_schema.ValidTextLine(title='Object int id as string'),
				 nti_schema.Number(title="Object int id")),
				title="The hit object")

class ISearchHit(IBaseHit, IMapping):
	"""
	represent an externalized search hit
	"""
	Query = nti_schema.Object(ISearchQuery, required=True, readonly=True)
	NTIID = nti_schema.ValidTextLine(title="hit object ntiid", required=False, readonly=True)
	OID = nti_schema.ValidTextLine(title="hit unique id", required=False, readonly=True)
	Snippet = nti_schema.ValidTextLine(title="text found", required=True, default=u'')
	Type = nti_schema.ValidTextLine(title="Search hit object type", required=True)
	Score = nti_schema.Float(title="Score for this hit", default=1.0, required=True)
	lastModified = nti_schema.Int(title="last modified date for this hit", default=0, required=True)

class INoteSearchHit(ISearchHit):
	pass

class IHighlightSearchHit(ISearchHit):
	pass

class IRedactionSearchHit(ISearchHit):
	pass

class IMessageInfoSearchHit(ISearchHit):
	pass

class IPostSearchHit(ISearchHit):
	pass

class IWhooshBookSearchHit(ISearchHit):
	pass

class IWhooshVideoTranscriptSearchHit(ISearchHit):
	pass

class IWhooshNTICardSearchHit(ISearchHit):
	pass

class ISearchHitComparator(interface.Interface):

	def compare(a, b):
		"""
		Compare arguments for for order. a or b can beither a IndexHit or ISearchHit
		"""

class IIndexHitMetaData(interface.Interface):
	"""Class to track index hit meta data"""

	last_modified = nti_schema.Number(title="Greatest last modified time",
									  required=True, readonly=True)
	type_count = schema.Dict(title="Index hit type count", required=True, readonly=True)
	total_hit_count = schema.Int(title='Total hit count', required=True, readonly=True)

	def track(ihit):
		"""
		track any metadata from the specified index hit
		"""

	def __iadd__(other):
		pass

class IBaseSearchResults(interface.Interface):
	query = schema.Object(ISearchQuery, title="Search query", required=True)

class ISearchResults(IBaseSearchResults):

	hits = nti_schema.IndexedIterable(
				value_type=schema.Object(IIndexHit, title="index hit"),
				title="IIndexHit objects",
				required=True,
				readonly=True)

	metadata = schema.Object(IIndexHitMetaData, title="Search hit metadata", required=False)

	def add(hit_or_hits):
		"""add a search hit(s) to this result"""

	def sort():
		"""sort the results based on the sortBy query param"""

	def __iadd__(other):
		pass

class ISuggestResults(IBaseSearchResults):

	suggestions = nti_schema.IndexedIterable(
						title="suggested words",
						required=True,
						readonly=True,
						value_type=nti_schema.ValidTextLine(title="suggested word"))

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

# highlights

class ISearchFragment(interface.Interface):

	text = schema.Text(title="fragment text", required=True, default=u'')

	matches = nti_schema.ListOrTuple(
					nti_schema.ListOrTuple(value_type=schema.Int(title='index', min=0),
										   min_length=2,
										   max_length=2),
					title="Iterable with pair tuples where a match occurs",
					min_length=0,
					required=True)

class IWhooshAnalyzer(interface.Interface):
	pass

# index events

class ISearchCompletedEvent(interface.Interface):
	user = schema.Object(nti_interfaces.IEntity, title="The search entity")
	query = schema.Object(ISearchQuery, title="The search query")
	metadata = schema.Object(IIndexHitMetaData, title="The result meta-data")
	elpased = schema.Float(title="The search elapsed time")

@interface.implementer(ISearchCompletedEvent)
class SearchCompletedEvent(component.interfaces.ObjectEvent):

	def __init__(self, user, query, metadata, elapsed=0):
		super(SearchCompletedEvent, self).__init__(user)
		self.query = query
		self.elapsed = elapsed
		self.metadata = metadata

	@property
	def user(self):
		return self.object
