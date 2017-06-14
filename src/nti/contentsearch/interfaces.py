#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Search interfaces.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import interface

from zope.component.interfaces import ObjectEvent

from zope.deprecation import deprecated

from zope.interface.common.sequence import IFiniteSequence

from nti.base.interfaces import IDict
from nti.base.interfaces import IList
from nti.base.interfaces import ITuple
from nti.base.interfaces import IString
from nti.base.interfaces import INumeric
from nti.base.interfaces import IUnicode
from nti.base.interfaces import IIterable
from nti.base.interfaces import ILastModified

from nti.dataserver.interfaces import IEntity

from nti.schema.field import Int
from nti.schema.field import Set
from nti.schema.field import Bool
from nti.schema.field import Dict
from nti.schema.field import Float
from nti.schema.field import Number
from nti.schema.field import Object
from nti.schema.field import Variant
from nti.schema.field import ValidText
from nti.schema.field import ListOrTuple
from nti.schema.field import IndexedIterable
from nti.schema.field import TextLine as ValidTextLine

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


deprecated('IBookContent', 'Use lastest index implementation')
class IBookContent(interface.Interface):
    pass


deprecated('INTICardContent', 'Use lastest index implementation')
class INTICardContent(interface.Interface):
    pass


deprecated('IContainerIDResolver', 'Use lastest index implementation')
class IContainerIDResolver(interface.Interface):
    pass


deprecated('IAudioTranscriptContent', 'Use lastest index implementation')
class IAudioTranscriptContent(interface.Interface):
    pass


deprecated('IVideoTranscriptContent', 'Use lastest index implementation')
class IVideoTranscriptContent(interface.Interface):
    pass


deprecated('IContentSearcher', 'Use lastest index implementation')
class IContentSearcher(interface.Interface):
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

    packages = ListOrTuple(ValidTextLine(title="Content NTIID to search on"),
                           required=False)

    searchOn = ListOrTuple(ValidTextLine(title="Content types to search on"),
                           required=False)

    creator = ValidTextLine(title="creator", required=False)

    creationTime = Object(IDateTimeRange, title="created date-time range",
                          required=False)

    modificationTime = Object(IDateTimeRange, title="last modified time-date range",
                              required=False)

    sortOn = ValidTextLine(title="Field or function to sort by",
                           required=False)

    origin = ValidTextLine(title="The raw NTIID where the search was invoked", 
                           required=False)

    sortOrder = ValidTextLine(title="descending or ascending  to sort order",
                              default='descending', required=False)

    applyHighlights = Bool(title="Apply search hit hilights", required=False,
                           default=True)

    IsEmpty = Bool(title="Returns true if this is an empty search",
                   required=True, readonly=True)
    IsEmpty.setTaggedValue('_ext_excluded_out', True)

    IsDescendingSortOrder = Bool(title="Returns true if the sortOrder is descending",
                                 required=True, readonly=True)
    IsDescendingSortOrder.setTaggedValue('_ext_excluded_out', True)

    context = Dict(ValidTextLine(title='name'),
                   Variant((Object(IString),
                            Object(IList),
                            Object(IDict),
                            Object(ITuple),
                            Object(INumeric),
                            Object(IUnicode)),
                           variant_raise_when_schema_provided=True,
                           title="The value"),
                   title="Search query context", required=False, default={})

    items = interface.Attribute('Attributes key/value in context')
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


class IRootPackageResolver(interface.Interface):
    """
    Interface for a registered utility that returns
    the root of a specified ntiid
    """

    def resolve(user, ntiid):
        pass


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
        :returns an iterator over the search results
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
                          default=None)
# search results


class ISearchHit(ILastModified):
    Query = interface.Attribute("Search query")
    Query.setTaggedValue('_ext_excluded_out', True)

    Score = Number(title="hit relevance score",
                   required=False,
                   default=1.0,
                   min=0.0)

    ID = ValidTextLine(title="hit unique id", required=True)

    NTIID = ValidTextLine(title="hit object ntiid", required=False)
    Creator = ValidTextLine(title="Search hit target creator", required=False)
    Containers = ListOrTuple(value_type=ValidTextLine(title="the ntiid"),
                             title="The containers",
                             required=False)

    Fragments = ListOrTuple(value_type=Object(ISearchFragment, title="the fragment"),
                            title="search fragments",
                            required=False)

    TargetMimeType = ValidTextLine(title="Target mimetype", required=True)

    Target = Object(interface.Interface,
                    title="the object hit",
                    required=False)
    Target.setTaggedValue('_ext_excluded_out', True)


class ITranscriptSearchHit(ISearchHit):
    EndMilliSecs = Number(title="Media end timestamp", required=False)
    StartMilliSecs = Number(title="Media start video timestamp",
                            required=False)


class IContentUnitSearchHit(ISearchHit):
    pass


class IUserGeneratedDataSearchHit(ISearchHit):
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

    __name__ = ValidTextLine(title='Predicate name', required=True)

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
                          title="Cointainer hit type count",
                          required=False)

    TotalHitCount = Int(title='Total hit count', required=True,
                        readonly=True, default=0)

    FilteredCount = Int(title='Total hit filtered', required=True,
                        readonly=False, default=0)

    FilteringPredicates = Set(title="Predicates that filter hits",
                              required=False)

    def track(hit):
        """
        track any metadata from the specified search hit
        """

    def __iadd__(other):
        pass


class IBaseSearchResults(interface.Interface):
    Name = ValidTextLine(title='Results name', required=False)
    Query = Object(ISearchQuery, title="Search query", required=True)


class ISearchResults(IBaseSearchResults, ILastModified):

    Hits = IndexedIterable(value_type=Object(ISearchHit, description="A ISearchHit`"),
                           title="search hit objects",
                           required=True)

    HitMetaData = Object(ISearchHitMetaData, 
                         title="Search hit metadata", 
                         required=False)

    def add(hit):
        """
        Add a search hit(s) to this result
        """

    def extend(hits):
        """
        Add search hit(s) to this result
        """

    def sort():
        """
        Sort the results based on the sortBy query param
        """

    def add_filter_record(item, predicate):
        """
        Indicates a record was filtered out by the given predicate.
        """

    def __iadd__(other):
        pass

    def __len__():
        pass

    def __iter__():
        pass


class ISuggestResults(IBaseSearchResults):

    Suggestions = IndexedIterable(title="suggested words",
                                  required=True,
                                  value_type=ValidTextLine(title="suggested word"))

    def add(word):
        """
        Add a word suggestion to this result
        """

    def extend(words):
        """
        Add a word suggestion(s) to this result
        """

    add_suggestions = add

    def __len__():
        pass

    def __iter__():
        pass


class ISearchResultsList(IIterable, IFiniteSequence):

    Query = Object(ISearchQuery, title="Search query", required=True)

    Items = IndexedIterable(value_type=Object(IBaseSearchResults, description="A search result"),
                            title="search reult",
                            required=False)


# index events


class ISearchCompletedEvent(interface.Interface):
    hit_count = Int(title='total hit count')
    elpased = Float(title="The search elapsed time")
    user = Object(IEntity, title="The search entity")
    query = Object(ISearchQuery, title="The search query")
    results = Object(ISearchResults, title="The results")


@interface.implementer(ISearchCompletedEvent)
class SearchCompletedEvent(ObjectEvent):

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
    def hit_count(self):
        return len(self.results)
    TotalHitCount = hit_count


class IResultTransformer(interface.Interface):
    """
    An adapter interface to transform an object into
    an appropriate object to return on hits.
    """
