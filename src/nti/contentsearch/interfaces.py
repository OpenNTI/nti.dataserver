#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Search interfaces.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import component
from zope import interface

from zope.container.interfaces import IContained

from zope.deprecation import deprecated

from zope.mimetype.interfaces import IContentTypeAware

from nti.dataserver.interfaces import IEntity
from nti.dataserver.interfaces import ILastModified

from nti.schema.field import Int
from nti.schema.field import Bool
from nti.schema.field import Dict
from nti.schema.field import Text
from nti.schema.field import Float
from nti.schema.field import Number
from nti.schema.field import Object
from nti.schema.field import Variant
from nti.schema.field import Iterable
from nti.schema.field import ValidText
from nti.schema.field import ListOrTuple
from nti.schema.field import ValidTextLine
from nti.schema.field import IndexedIterable

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
	endTime = Number(title="End date/time", required=False)
	startTime = Number(title="Start date/time", required=False)

class ISearchQuery(interface.Interface):

	term = ValidTextLine(title="Query search term", required=True)

	username = ValidTextLine(title="User doing the search", required=False)

	language = ValidTextLine(title="Query search term language", required=False,
							 default='en')

	limit = Int(title="search results limit", required=False, default=None)

	packages = ListOrTuple(ValidTextLine(title="Book content NTIID to search on"),
						   required=False)

	searchOn = ListOrTuple(ValidTextLine(title="Content types to search on"),
						   required=False)

	creator = ValidTextLine(title="creator", required=False)

	creationTime = Object(IDateTimeRange, title="created date-time range",
						  required=False)

	modificationTime = Object(IDateTimeRange, title="last modified time-date range",
							  required=False)

	sortOn = ValidTextLine(title="Field or function to sort by", required=False)

	location = ValidTextLine(title="The reference NTIID where the search was invoked",
							 required=False)

	origin = ValidTextLine(title="The raw NTIID where the search was invoked", required=False)

	sortOrder = ValidTextLine(title="descending or ascending  to sort order",
							  default='descending', required=False)

	applyHighlights = Bool(title="Apply search hit hilights", required=False,
						   default=True)

	batchSize = Int(title="page size", required=False)

	batchStart = Int(title="The index of the first object to return, starting with zero",
					 required=False, min=0)

	context = Dict(ValidTextLine(title='name'),
				   ValidTextLine(title='value'),
				   title="Search query context", required=False, default={})

	IsEmpty = Bool(title="Returns true if this is an empty search",
				   required=True, readonly=True)

	IsPrefixSearch = Bool(title="Returns true if the search is for prefix search",
						  required=True, readonly=True)

	IsPhraseSearch = Bool(title="Returns true if the search is for phrase search",
					      required=True, readonly=True)

	IsDescendingSortOrder = Bool(title="Returns true if the sortOrder is descending",
							 	 required=True, readonly=True)

	IsBatching = Bool(title="Returns true if this is a batch search",
				 	  required=True, readonly=True)

	items = interface.Attribute('Attributes key/value not in the interface')
	items.setTaggedValue('_ext_excluded_out', True)

	# TODO: to remove
	surround = Int(title="Highlight surround chars", required=False, default=50, min=1)

	maxchars = Int(title="Highlight max chars", required=False, default=300, min=1)

	prefix = Int(title="Suggestion prefix", required=False, min=1)

	threshold = Number(title="Suggestion threshold", required=False,
					   default=0.4999, min=0.0)

	maxdist = Int(title="Maximun edit distance from the given word to look at",
				  required=False, default=15, min=2)

	decayFactor = Number(title="decay factor", required=False, min=0.001, max=1.0, default=0.94)

	site_names = ListOrTuple(ValidTextLine(title="Site names"), required=False)
	site_names.setTaggedValue('_ext_excluded_out', True)

class ISearchQueryValidator(interface.Interface):

	def validate(query):
		"""check if the specified search query is valid"""

class ISearchQueryParser(interface.Interface):

	def parse(query):
		"""parse the specified query"""

# searcher

class ISearchPackageResolver(interface.Interface):
	"""
	Interface for registered subscribers that returns
	a list of pkgs ntiids for the specied user and
	source ntiid
	"""

	def resolve(user, ntiid):
		pass

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

class IContentSearcher(ISearcher,
					   IContained):
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

	def ctor_args():
		"""
		return a dictionary with the arguments to be passed to an index writer constructor
		"""

	def commit_args():
		"""
		return a dictionary with the arguments to be passed to an index writer commit method
		"""

# content

class IBaseContent(ILastModified):
	pass

class IWhooshContent(IContentTypeAware):
	pass

class IBookContent(IBaseContent):
	ntiid = ValidTextLine(title="NTIID", required=True)
	title = ValidText(title="Content title", required=True)
	content = ValidText(title="Text content", required=True)

class IWhooshBookContent(IBookContent, IWhooshContent):
	docnum = Int(title="Document number", required=True)
	score = Number(title="Search score", required=False, default=1.0)

class IMediaTranscriptContent(IBaseContent):
	containerId = ValidTextLine(title="NTIID of video container", required=True)
	content = ValidText(title="Text content", required=True)
	title = ValidText(title="Video title", required=False)
	start_millisecs = Float(title="Start timestamp", required=True)
	end_millisecs = Float(title="End timestamp", required=True)

class IWhooshMediaTranscriptContent(IMediaTranscriptContent, IWhooshContent):
	docnum = Int(title="Document number", required=False)
	score = Number(title="Search score", required=False, default=1.0)

class IVideoTranscriptContent(IMediaTranscriptContent):
	videoId = ValidTextLine(title="Either the video NTIID or Id", required=True)

class IWhooshVideoTranscriptContent(IVideoTranscriptContent, IWhooshMediaTranscriptContent):
	pass

class IAudioTranscriptContent(IMediaTranscriptContent):
	audioId = ValidTextLine(title="Either the audio NTIID or Id", required=True)

class IWhooshAudioTranscriptContent(IAudioTranscriptContent, IWhooshMediaTranscriptContent):
	pass

class INTICardContent(IBaseContent):
	href = ValidTextLine(title="card href", required=False)
	ntiid = ValidTextLine(title="card NTIID", required=True)
	title = ValidTextLine(title="Card title", required=True)
	creator = ValidTextLine(title="Card creator", required=True)
	description = ValidTextLine(title="Card description", required=True)
	target_ntiid = ValidTextLine(title="card target ntiid", required=False)
	containerId = ValidTextLine(title="card container ntiid", required=False)

class IWhooshNTICardContent(INTICardContent, IWhooshContent):
	docnum = Int(title="Document number", required=False)
	score = Number(title="Search score", required=False, default=1.0)


class IWhooshQueryParser(ISearchQueryParser):

	def parse(qo, schema=None):
		pass

# user generated content resolvers

class ISearchTypeMetaData(interface.Interface):
	Name = ValidTextLine(title="Search type name", readonly=True)
	MimeType = ValidTextLine(title="Search object mimeType", readonly=True)
	IsUGD = Bool(title="Is user generated data", default=True, readonly=True)
	Order = Int(title="Search order", default=99, readonly=True, required=False)
	Interface = Object(interface.Interface, title="Object Interface", readonly=True)

class IACLResolver(interface.Interface):

	acl = ListOrTuple(ValidTextLine(title="entity username"),
					  title='username', default=())

class ITypeResolver(interface.Interface):

	type = ValidTextLine(title="content type", default=None)

class IContentResolver(interface.Interface):

	content = ValidTextLine(title="content to index", default=None)

class INTIIDResolver(interface.Interface):

	ntiid = ValidTextLine(title="NTIID identifier", default=None)

class IContainerIDResolver(interface.Interface):

	containerId = ValidTextLine(title="container identifier", default=None)

class ILastModifiedResolver(interface.Interface):

	lastModified = Float(title="last modified date", default=0.0)

class ICreatedTimeResolver(interface.Interface):

	createdTime = Float(title="created date", default=0.0)

class ICreatorResolver(interface.Interface):

	creator = ValidTextLine(title="creator user", default=None)

class ITitleResolver(interface.Interface):

	title = ValidTextLine(title="object title", default=None)

class ITagsResolver(interface.Interface):

	tags = ListOrTuple(ValidTextLine(title="tag"), title='tags', default=())

class IKeywordsResolver(interface.Interface):

	keywords = ListOrTuple(ValidTextLine(title="keyword"), title='keywords', default=())

class IShareableContentResolver(interface.Interface):

	sharedWith = ListOrTuple(ValidTextLine(title="username"), title='sharedWith', default=())

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

	inReplyTo = ValidTextLine(title="inReplyTo ntiid", default=None)

class IHighlightContentResolver(IThreadableContentResolver):
	pass

class IRedactionContentResolver(IHighlightContentResolver):

	replacementContent = ValidTextLine(title="replacement content",
												  default=None)

	redactionExplanation = ValidTextLine(title="replacement explanation",
													default=None)

class INoteContentResolver(IHighlightContentResolver, ITitleResolver):

	references = ListOrTuple(ValidTextLine(title="ntiid"), title='nttids references',
							 default=())

class IMessageInfoContentResolver(IThreadableContentResolver):

	id = ValidTextLine(title="message id", default=None)

	channel = ValidTextLine(title="message channel", default=None)

	recipients = ListOrTuple(ValidTextLine(title="username"), title='message recipients',
							 default=())

class IBlogContentResolver(_ContentMixinResolver,
							ICreatorResolver,
						  	IShareableContentResolver,
						  	ITitleResolver,
						  	ITagsResolver):

	id = ValidTextLine(title="post id", default=None)

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

class IAudioTranscriptContentResolver(_ContentMixinResolver):
	pass

class INTICardContentResolver(_ContentMixinResolver, ICreatorResolver):

	title = ValidTextLine(title="card title", default=None)

class IModeledContentResolver(IPostContentResolver,
							  IMessageInfoContentResolver,
							  IRedactionContentResolver,
							  IHighlightContentResolver,
							  INoteContentResolver):
	pass

# highlights

class ISearchFragment(interface.Interface):

	text = Text(title="fragment text", required=True, default=u'')

	matches = ListOrTuple(
					ListOrTuple(value_type=Int(title='index', min=0),
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
	Query = Object(ISearchQuery, title="Search query", required=False)
	Score = Number(title="hit relevance score", required=False, default=1.0, min=0.0)

class ISearchHit(IBaseHit, ILastModified):
	"""
	represent an externalized search hit
	"""
	OID = ValidTextLine(title="hit unique id", required=True)
	NTIID = ValidTextLine(title="hit object ntiid", required=False)
	Snippet = ValidTextLine(title="text found", required=False, default=u'')
	Type = ValidTextLine(title="Search hit object type", required=True)
	Creator = ValidTextLine(title="Search hit target creator", required=False)
	ContainerId = Variant((ValidTextLine(title="The ntiid"),
						   ListOrTuple(value_type=ValidTextLine(title="the ntiid"))),
						  title="The containers")
	Fragments = ListOrTuple(value_type=Object(ISearchFragment, title="the fragment"),
							title="search fragments", required=False)

	TargetMimeType = ValidTextLine(title="Target mimetype", required=True)
	Target = Object(interface.Interface, title="the object hit", required=False)
	Target.setTaggedValue('_ext_excluded_out', True)

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
	Title = ValidTextLine(title="Book title", required=False)

class IWhooshBookSearchHit(IBookSearchHit):
	pass

class IMediaTranscriptSearchHit(IContentSearchHit):
	Title = ValidTextLine(title="Card title", required=False)
	EndMilliSecs = Number(title="Video end video timestamp", required=False)
	StartMilliSecs = Number(title="video start video timestamp", required=False)

class IWhooshMediaTranscriptSearchHit(IMediaTranscriptSearchHit):
	pass

class IAudioTranscriptSearchHit(IMediaTranscriptSearchHit):
	AudioID = ValidTextLine(title="Audio NTIID", required=True)

class IWhooshAudioTranscriptSearchHit(IWhooshMediaTranscriptSearchHit, IAudioTranscriptSearchHit):
	pass

class IVideoTranscriptSearchHit(IMediaTranscriptSearchHit):
	VideoID = ValidTextLine(title="Video NTIID", required=True)

class IWhooshVideoTranscriptSearchHit(IWhooshMediaTranscriptSearchHit, IVideoTranscriptSearchHit):
	pass

class INTICardSearchHit(IContentSearchHit):
	Href = ValidTextLine(title="Card HREF", required=True)
	Title = ValidTextLine(title="Card title", required=False)
	TargetNTIID = ValidTextLine(title="Card target NTIID", required=True)

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
	Search hit filter - implemented as subscriber.
	"""

	def allow(item, score=1.0, query=None):
		"""
		allow a search hit into the results
		"""

class ISearchHitPostProcessingPredicate(interface.Interface):
	"""
	Search hit predicate filter meant to run after `ISearchHitPredicate`
	subscribers.
	"""
	# XXX: Dupe ISearchHitPredicate for now
	def allow(item, score=1.0, query=None):
		"""
		allow a search hit into the results
		"""

class ISearchHitMetaData(ILastModified):
	"""Class to track search hit meta data"""

	TypeCount = Dict(ValidTextLine(title='type'),
					 Int(title='count'),
					 title="Search hit type count", required=True)

	SearchTime = Number(title='Search time', required=True, default=0)

	ContainerCount = Dict(
						ValidTextLine(title='container'),
						Int(title='count'),
						title="Cointainer hit type count", required=True)

	TotalHitCount = Int(title='Total hit count', required=True,
						readonly=True, default=0)

	FilteredCount = Int(title='Total hit filtered', required=True,
						readonly=False, default=0)

	def track(hit):
		"""
		track any metadata from the specified search hit
		"""

	def __iadd__(other):
		pass

class IBaseSearchResults(ILastModified):
	Query = Object(ISearchQuery, title="Search query", required=True)

class ISearchResults(IBaseSearchResults):

	Hits = IndexedIterable(
				value_type=Object(ISearchHit, description="A ISearchHit`"),
				title="search hit objects",
				required=True)

	ContentHits = Iterable(
						title="content search hit objects",
						required=False,
						readonly=True)

	UserDataHits = Iterable(
						title="user generated data search hit objects",
						required=False,
						readonly=True)

	HitMetaData = Object(ISearchHitMetaData, title="Search hit metadata", required=False)

	def add(hit, score=1.0):
		"""add a search hit(s) to this result"""

	def extend(hits):
		"""add a search hit(s) to this result"""

	def sort():
		"""sort the results based on the sortBy query param"""

	def __iadd__(other):
		pass

class ISuggestResults(IBaseSearchResults):

	Suggestions = IndexedIterable(
						title="suggested words",
						required=True,
						value_type=ValidTextLine(title="suggested word"))

	def add(word):
		"""add a word suggestion to this result"""

	def extend(words):
		"""add a word suggestion(s) to this result"""

	add_suggestions = add

class ISuggestAndSearchResults(ISearchResults, ISuggestResults):

	Suggestions = IndexedIterable(
						title="suggested words",
						required=False,
						value_type=ValidTextLine(title="suggested word"))

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
	elpased = Float(title="The search elapsed time")
	query = Object(ISearchQuery, title="The search query")
	user = Object(IEntity, title="The search entity")
	metadata = Object(ISearchHitMetaData, title="The result meta-data")
	results = Object(IBaseSearchResults, title="The results")

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

import zope.deferredimport
zope.deferredimport.initialize()
zope.deferredimport.deprecatedFrom(
	"Moved to nti.contentprocessing.interfaces",
	"nti.contentprocessing.interfaces",
	"IStopWords"
)

zope.deferredimport.deprecatedFrom(
	"Moved to nti.contentindexing.interfaces",
	"nti.contentindexing.interfaces",
	"IContentSchemaCreator",
	"IBookSchemaCreator",
	"INTICardSchemaCreator",
	"IAudioTranscriptSchemaCreator",
	"IVideoTranscriptSchemaCreator"
)

zope.deferredimport.deprecatedFrom(
	"Moved to nti.contentindexing.whoosh.interfaces",
	"nti.contentindexing.whooshidx.interfaces",
	"IWhooshBookSchemaCreator",
	"IWhooshNTICardSchemaCreator",
	"IWhooshAudioTranscriptSchemaCreator",
	"IWhooshVideoTranscriptSchemaCreator",
)
