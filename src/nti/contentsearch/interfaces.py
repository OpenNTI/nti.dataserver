#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Search interfaces.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import schema
from zope import component
from zope import interface
from zope.deprecation import deprecated
from zope.mimetype import interfaces as zmime_interfaces

from nti.dataserver import interfaces as nti_interfaces

from nti.utils import schema as nti_schema

# deprecated interfaes

deprecated('IRepozeDataStore', 'Use lastest index implementation')
class IRepozeDataStore(interface.Interface):
	pass

deprecated('IRepozeEntityIndexManager', 'Use lastest index implementation')
class IRepozeEntityIndexManager(interface.Interface):
	pass

deprecated('IEntityIndexManager', 'Use lastest index implementation')
class IEntityIndexManager(interface.Interface):
	pass

# search query

class IDateTimeRange(interface.Interface):
	startTime = nti_schema.Number(title="Start date/time", required=False)
	endTime = nti_schema.Number(title="End date/time", required=False)

class ISearchQuery(interface.Interface):

	term = nti_schema.ValidTextLine(title="Query search term", required=True)
	username = nti_schema.ValidTextLine(title="User doing the search", required=False)
	language = nti_schema.ValidTextLine(title="Query search term language", required=False,
										default='en')

	limit = schema.Int(title="search results limit", required=False, default=None)

	indexid = nti_schema.ValidTextLine(title="Book content NTIID", required=False)

	searchOn = nti_schema.ListOrTuple(nti_schema.ValidTextLine(title="Content types to search on"),
									  required=False)

	creator = nti_schema.ValidTextLine(title="creator", required=False)
	creationTime = nti_schema.Object(IDateTimeRange, title="created date-time range", required=False)
	modificationTime = nti_schema.Object(IDateTimeRange, title="last modified time-date range", required=False)

	sortOn = nti_schema.ValidTextLine(title="Field or function to sort by", required=False)

	location = nti_schema.ValidTextLine(title="The reference NTIID where the search was invoked",
										required=False)
	sortOrder = nti_schema.ValidTextLine(title="descending or ascending  to sort order",
										 default='descending', required=False)

	surround = schema.Int(title="Hightlight surround chars", required=False,
						  default=50, min=1)

	maxchars = schema.Int(title="Hightlight max chars", required=False,
						  default=300, min=1)

	prefix = schema.Int(title="Suggestion prefix", required=False, min=1)
	threshold = nti_schema.Number(title="Suggestion threshold", required=False,
								  default=0.4999, min=0.0)
	maxdist = schema.Int(title="Maximun edit distance from the given word to look at",
						 required=False, default=15, min=2)

	applyHighlights = schema.Bool(title="Apply search hit hilights", required=False, default=True)

	batchSize = schema.Int(title="page size", required=False)
	batchStart = schema.Int(title="The index of the first object to return, starting with zero",
						    required=False, min=0)

	decayFactor = nti_schema.Number(title="decay factor", required=False, min=0.001, max=1.0, default=0.94)

	IsEmpty = schema.Bool(title="Returns true if this is an empty search",
						   required=True, readonly=True)

	IsPrefixSearch = schema.Bool(title="Returns true if the search is for prefix search",
								 required=True, readonly=True)

	IsPhraseSearch = schema.Bool(title="Returns true if the search is for phrase search",
								 required=True, readonly=True)

	IsDescendingSortOrder = schema.Bool(title="Returns true if the sortOrder is descending",
								 		required=True, readonly=True)

	IsBatching = schema.Bool(title="Returns true if this is a batch search",
							 required=True, readonly=True)


class ISearchQueryValidator(interface.Interface):

	def validate(query):
		"""check if the specified search query is valid"""

class ISearchQueryParser(interface.Interface):

	def parse(query):
		"""parse the specified query"""

# searcher

class ISearcher(interface.Interface):

	def search(query, *args, **kwargs):
		"""
		search the content using the specified query

		:param query: Search query
		"""

	def suggest(query, *args, **kwargs):
		"""
		perform a word suggestion

		:param query: Search query
		"""

	def suggest_and_search(query, *args, **kwargs):
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

# content

class IBaseContent(nti_interfaces.ILastModified):
	pass

class IWhooshContent(zmime_interfaces.IContentTypeAware):
	pass

class IBookContent(IBaseContent):
	ntiid = nti_schema.ValidTextLine(title="NTIID", required=True)
	title = nti_schema.ValidText(title="Content title", required=True)
	content = nti_schema.ValidText(title="Text content", required=True)

class IWhooshBookContent(IBookContent, IWhooshContent):
	docnum = schema.Int(title="Document number", required=True)
	score = nti_schema.Number(title="Search score", required=False, default=1.0)

class IVideoTranscriptContent(IBaseContent):
	containerId = nti_schema.ValidTextLine(title="NTIID of video container", required=True)
	videoId = nti_schema.ValidTextLine(title="Either the video NTIID or Id", required=True)
	content = nti_schema.ValidText(title="Text content", required=True)
	title = nti_schema.ValidText(title="Video title", required=False)
	start_millisecs = schema.Float(title="Start timestamp", required=True)
	end_millisecs = schema.Float(title="End timestamp", required=True)

class IWhooshVideoTranscriptContent(IVideoTranscriptContent, IWhooshContent):
	docnum = schema.Int(title="Document number", required=False)
	score = nti_schema.Number(title="Search score", required=False, default=1.0)

class INTICardContent(IBaseContent):
	href = nti_schema.ValidTextLine(title="card href", required=False)
	ntiid = nti_schema.ValidTextLine(title="card NTIID", required=True)
	title = nti_schema.ValidTextLine(title="Card title", required=True)
	creator = nti_schema.ValidTextLine(title="Card creator", required=True)
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

class ISearchTypeMetaData(interface.Interface):
	Name = nti_schema.ValidTextLine(title="Search type name", readonly=True)
	MimeType = nti_schema.ValidTextLine(title="Search object mimeType", readonly=True)
	IsUGD = nti_schema.Bool(title="Is user generated data", default=True, readonly=True)
	Order = nti_schema.Int(title="Search order", default=99, readonly=True, required=False)
	Interface = nti_schema.Object(interface.Interface, title="Object Interface", readonly=True)

class IACLResolver(interface.Interface):

	acl = nti_schema.ListOrTuple(nti_schema.ValidTextLine(title="entity username"),
								 title='username', default=())

class ITypeResolver(interface.Interface):

	type = nti_schema.ValidTextLine(title="content type", default=None)

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


class ContentMixinResolver(ITypeResolver,
						   IContentResolver,
						   INTIIDResolver,
						   IContainerIDResolver,
						   ILastModifiedResolver,
						   ICreatedTimeResolver):
	pass
_ContentMixinResolver = ContentMixinResolver  # BWC

class IUserContentResolver(ContentMixinResolver, ICreatorResolver):
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

class IForumContentResolver(_ContentMixinResolver,
							ICreatorResolver,
						  	IShareableContentResolver,
						  	ITitleResolver):
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


# highlights

class ISearchFragment(interface.Interface):

	text = schema.Text(title="fragment text", required=True, default=u'')

	matches = nti_schema.ListOrTuple(
					nti_schema.ListOrTuple(value_type=schema.Int(title='index', min=0),
										   min_length=2,
										   max_length=2),
					title="Iterable with pair tuples where a match occurs",
					min_length=0,
					required=True,
					default=[])
# search results

class IBaseHit(interface.Interface):
	"""
	represent a base search hit
	"""
	Query = schema.Object(ISearchQuery, title="Search query", required=False)
	Score = nti_schema.Number(title="hit relevance score", required=False, default=1.0, min=0.0)

class ISearchHit(IBaseHit, nti_interfaces.ILastModified):
	"""
	represent an externalized search hit
	"""
	OID = nti_schema.ValidTextLine(title="hit unique id", required=True)
	NTIID = nti_schema.ValidTextLine(title="hit object ntiid", required=False)
	Snippet = nti_schema.ValidTextLine(title="text found", required=False, default=u'')
	Type = nti_schema.ValidTextLine(title="Search hit object type", required=True)
	Creator = nti_schema.ValidTextLine(title="Search hit target creator", required=False)
	ContainerId = nti_schema.ValidTextLine(title="Search hit container id", required=False)
	TargetMimeType = nti_schema.ValidTextLine(title="Search hit target mimetype", required=True)
	Fragments = nti_schema.ListOrTuple(value_type=schema.Object(ISearchFragment, title="the fragment"),
									   title="search fragments", required=False)

class IUserDataSearchHit(ISearchHit):
	"""
	marker interface for user generated data search hits
	"""

class INoteSearchHit(IUserDataSearchHit):
	pass

class IHighlightSearchHit(IUserDataSearchHit):
	pass

class IRedactionSearchHit(IUserDataSearchHit):
	pass

class IMessageInfoSearchHit(IUserDataSearchHit):
	pass

class IPostSearchHit(IUserDataSearchHit):
	pass

class IForumSearchHit(IUserDataSearchHit):
	pass

class IContentSearchHit(ISearchHit):
	"""
	marker interface for content search hits
	"""

class IBookSearchHit(IContentSearchHit):
	Title = nti_schema.ValidTextLine(title="Book title", required=False)

class IWhooshBookSearchHit(IBookSearchHit):
	pass

class IVideoTranscriptSearchHit(IContentSearchHit):
	Title = nti_schema.ValidTextLine(title="Card title", required=False)
	VideoID = nti_schema.ValidTextLine(title="Video NTIID", required=True)
	EndMilliSecs = nti_schema.Number(title="Video end video timestamp", required=False)
	StartMilliSecs = nti_schema.Number(title="video start video timestamp", required=False)

class IWhooshVideoTranscriptSearchHit(IVideoTranscriptSearchHit):
	pass

class INTICardSearchHit(IContentSearchHit):
	Href = nti_schema.ValidTextLine(title="Card HREF", required=True)
	Title = nti_schema.ValidTextLine(title="Card title", required=False)
	TargetNTIID = nti_schema.ValidTextLine(title="Card target NTIID", required=True)

class IWhooshNTICardSearchHit(INTICardSearchHit):
	pass

class ISearchHitComparator(interface.Interface):

	def compare(a, b):
		pass

class ISearchHitComparatorFactory(interface.Interface):

	def __call__(result):
		"""
		return an instance of a ISearchHitComparator
		"""

class ISearchHitPredicate(interface.Interface):
	"""
	Search hit filter - implemented as subscriber"
	"""

	def allow(item, score=1.0):
		"""
		allow a search hit into the results
		"""

class ISearchHitMetaData(nti_interfaces.ILastModified):
	"""Class to track search hit meta data"""

	TypeCount = schema.Dict(nti_schema.ValidTextLine(title='type'),
							nti_schema.Int(title='count'),
							title="Search hit type count", required=True)

	SearchTime = nti_schema.Number(title='Search time', required=True, default=0)

	ContainerCount = schema.Dict(
						nti_schema.ValidTextLine(title='container'),
						nti_schema.Int(title='count'),
						title="Cointainer hit type count", required=True)

	TotalHitCount = schema.Int(title='Total hit count', required=True,
							   readonly=True, default=0)

	def track(hit):
		"""
		track any metadata from the specified search hit
		"""

	def __iadd__(other):
		pass

class IBaseSearchResults(nti_interfaces.ILastModified):
	Query = schema.Object(ISearchQuery, title="Search query", required=True)

class ISearchResults(IBaseSearchResults):

	Hits = nti_schema.IndexedIterable(
				value_type=nti_schema.Object(ISearchHit, description="A ISearchHit`"),
				title="search hit objects",
				required=True)

	ContentHits = schema.Iterable(
						title="content search hit objects",
						required=False,
						readonly=True)

	UserDataHits = schema.Iterable(
						title="user generated data search hit objects",
						required=False,
						readonly=True)

	HitMetaData = schema.Object(ISearchHitMetaData, title="Search hit metadata", required=False)

	def add(hit, score=1.0):
		"""add a search hit(s) to this result"""

	def extend(hits):
		"""add a search hit(s) to this result"""

	def sort():
		"""sort the results based on the sortBy query param"""

	def __iadd__(other):
		pass

class ISuggestResults(IBaseSearchResults):

	Suggestions = nti_schema.IndexedIterable(
						title="suggested words",
						required=True,
						value_type=nti_schema.ValidTextLine(title="suggested word"))

	def add(word):
		"""add a word suggestion to this result"""

	def extend(words):
		"""add a word suggestion(s) to this result"""

	add_suggestions = add

class ISuggestAndSearchResults(ISearchResults, ISuggestResults):

	Suggestions = nti_schema.IndexedIterable(
						title="suggested words",
						required=False,
						value_type=nti_schema.ValidTextLine(title="suggested word"))

class ISearchResultsCreator(interface.Interface):

	def __call__(query):
		"""return a new instance of a ISearchResults"""

class ISuggestResultsCreator(interface.Interface):

	def __call__(query):
		"""return a new instance of a ISuggestResults"""

class ISuggestAndSearchResultsCreator(interface.Interface):

	def __call__(query):
		"""return a new instance of a ISuggestAndSearchResults"""


class IWhooshAnalyzer(interface.Interface):
	pass

# index events

class ISearchCompletedEvent(interface.Interface):
	elpased = schema.Float(title="The search elapsed time")
	query = schema.Object(ISearchQuery, title="The search query")
	user = schema.Object(nti_interfaces.IEntity, title="The search entity")
	metadata = schema.Object(ISearchHitMetaData, title="The result meta-data")
	results = schema.Object(IBaseSearchResults, title="The results")

@interface.implementer(ISearchCompletedEvent)
class SearchCompletedEvent(component.interfaces.ObjectEvent):

	def __init__(self, user, results, elapsed=0):
		super(SearchCompletedEvent, self).__init__(user)
		self.results = results
		self.elapsed = elapsed

	@property
	def user(self):
		return self.object

	@property
	def query(self):
		return self.results.Query

	@property
	def metadata(self):
		return getattr(self.results, 'HitMetaData', None)
