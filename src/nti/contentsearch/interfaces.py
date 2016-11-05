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

deprecated('IEntityIndexController', 'Use lastest index implementation')
class IEntityIndexController(interface.Interface):
	pass

deprecated('IIndexManager', 'Use lastest index implementation')
class IIndexManager(interface.Interface):
	pass

deprecated('IWhooshIndexStorage', 'Use lastest index implementation')
class IWhooshIndexStorage(interface.Interface):
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

class ISearchQueryValidator(interface.Interface):

	def validate(query):
		"""
		Check if the specified search query is valid
		"""

class ISearchQueryParser(interface.Interface):

	def parse(query):
		"""
		parse the specified query
		"""

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

# highlights

class ISearchFragment(interface.Interface):
	Field = ValidTextLine(title="Matching field", required=True)
	Matches = ListOrTuple(value_type=ValidText(title='Snippet text'),
						  title="Snippet text",
						  min_length=0,
						  required=True,
						  default=())
# search results

class ISearchHit(ILastModified):
	Query = Object(ISearchQuery, title="Search query", required=False)
	Score = Number(title="hit relevance score", required=False, default=1.0, min=0.0)

	ID = ValidTextLine(title="hit unique id", required=True)
	NTIID = ValidTextLine(title="hit object ntiid", required=False)
	Creator = ValidTextLine(title="Search hit target creator", required=False)
	ContainerId = ListOrTuple(value_type=ValidTextLine(title="the ntiid"),
						 	  title="The containers")
	
	Fragments = ListOrTuple(value_type=Object(ISearchFragment, title="the fragment"),
							title="search fragments", required=False)

	TargetMimeType = ValidTextLine(title="Target mimetype", required=True)

	Target = Object(interface.Interface, title="the object hit", required=False)
	Target.setTaggedValue('_ext_excluded_out', True)

class ITranscriptSearchHit(ISearchHit):	
	EndMilliSecs = Number(title="Media end timestamp", required=False)
	StartMilliSecs = Number(title="Media start video timestamp", required=False)

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

	TypeCount = Dict(ValidTextLine(title='type'),
					 Int(title='count'),
					 title="Search hit type count", required=True)

	SearchTime = Number(title='Search time', required=True, default=0)

	ContainerCount = Dict(ValidTextLine(title='container'),
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

	Name = ValidTextLine(title='Results name', required=False)

	Hits = IndexedIterable(
				value_type=Object(ISearchHit, description="A ISearchHit`"),
				title="search hit objects",
				required=True)

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

class IResultTransformer(interface.Interface):
	"""
	An adapter interface to transform an object into
	an appropriate object to return on hits.
	"""
