# -*- coding: utf-8 -*-
"""
Search results

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import numbers
import collections

from zope import interface
from zope import component
from zope.container import contained as zcontained
from zope.mimetype import interfaces as zmime_interfaces

from nti.mimetype.mimetype import nti_mimetype_with_class

from nti.utils.sort import isorted
from nti.utils.property import alias

from . import discriminators
from . import interfaces as search_interfaces

@interface.implementer(search_interfaces.IIndexHit)
class IndexHit(zcontained.Contained):

	__external_can_create__ = True
	mime_type = mimeType = 'application/vnd.nextthought.search.indexhit'

	ref = alias('Ref')
	score = alias('Score')

	def __init__(self, obj=None, score=None):
		super(IndexHit,self).__init__()
		self.Ref = obj
		self.Score = score

	@property
	def obj(self):
		result = self.Ref
		if isinstance(self.Ref, (numbers.Integral, six.string_types)):
			result = discriminators.get_object(int(self.ref))
		return result

	@property
	def Query(self):
		return None if self.__parent__ is None else self.__parent__.query
	query = Query

	def __repr__(self):
		return '%s(%s,%s)' % (self.__class__.__name__, self.Ref, self.score)
	__str__ = __repr__

	def __eq__(self, other):
		try:
			return self is other or (self.Ref == other.Ref and self.Score == other.Score)
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.Ref)
		xhash ^= hash(self.Score)
		return xhash

@interface.implementer(search_interfaces.IIndexHitMetaData)
class IndexHitMetaData(object):

	unspecified_container = u'+++unspecified_container+++'
	mime_type = mimeType = nti_mimetype_with_class('IndexHitMetaData')

	def __init__(self):
		self.lastModified = 0
		self.type_count = collections.defaultdict(int)
		self.container_count = collections.defaultdict(int)

	@property
	def last_modified(self):
		return self.lastModified
	LastModified = last_modified

	@property
	def total_hit_count(self):
		return sum(self.type_count.values())
	TotalHitCount = total_hit_count

	@property
	def TypeCount(self):
		return dict(self.type_count)

	@property
	def ContainerCount(self):
		return dict(self.container_count)

	def track(self, ihit):
		selected = ihit.obj

		# container count
		resolver = search_interfaces.IContainerIDResolver(selected, None)
		containerId = resolver.containerId if resolver else self.unspecified_container
		self.container_count[containerId] = self.container_count[containerId] + 1

		# last modified
		resolver = search_interfaces.ILastModifiedResolver(selected, None)
		lastModified = resolver.lastModified if resolver else 0
		self.lastModified = max(self.lastModified, lastModified or 0)

		# type count
		resolver = search_interfaces.ITypeResolver(selected, None)
		type_name = resolver.type if resolver else 0
		self.type_count[type_name] = self.type_count[type_name] + 1

	def __iadd__(self, other):
		# container count
		for k, v in other.container_count.items():
			self.container_count[k] = self.container_count[k] + v

		# last modified
		self.lastModified = max(self.lastModified, other.lastModified)

		# container count
		for k, v in other.type_count.items():
			self.type_count[k] = self.type_count[k] + v

		return self

class _MetaSearchResults(type):

	def __new__(cls, name, bases, dct):
		t = type.__new__(cls, name, bases, dct)
		t.mime_type = t.mimeType = nti_mimetype_with_class(name[1:])
		t.parameters = dict()
		return t

class _BaseSearchResults(zcontained.Contained):

	sorted = False

	def __init__(self, query):
		super(_BaseSearchResults,self).__init__()
		assert search_interfaces.ISearchQuery.providedBy(query)
		self._query = query

	def __str__(self):
		return self.__repr__()

	def __repr__(self):
		return '%s(hits=%s)' % (self.__class__.__name__, self.total)

	@property
	def query(self):
		return self._query

	@property
	def hits(self):
		raise NotImplementedError()

	@property
	def total(self):
		return len(self.hits)

	def __len__(self):
		return len(self.hits)

	def __getitem__(self, n):
		return self.hits[n]

	def __iter__(self):
		return iter(self.hits)

@interface.implementer(search_interfaces.ISearchResults,
					   zmime_interfaces.IContentTypeAware)
class _SearchResults(_BaseSearchResults):

	__metaclass__ = _MetaSearchResults

	def __init__(self, query):
		super(_SearchResults, self).__init__(query)
		self._hits = []
		self._ihitmeta = IndexHitMetaData()

	@property
	def hits(self):
		return self._hits

	@property
	def metadata(self):
		return self._ihitmeta

	def _add(self, item):
		ihit = None
		if search_interfaces.IIndexHit.providedBy(item):
			if item.ref is not None:
				ihit = item
		elif isinstance(item, tuple):
			if item[0] is not None:
				ihit = IndexHit(item[0], item[1])
		elif item is not None:
			ihit = IndexHit(item, 1.0)

		if ihit is not None:
			self.sorted = False
			ihit.__parent__ = self  # make sure the parent is set
			self._hits.append(ihit)
			self._ihitmeta.track(ihit)

	def add(self, hits):
		if search_interfaces.IIndexHit.providedBy(hits) or isinstance(hits, tuple):
			self._add(hits)
		else:
			items = [hits] if not isinstance(hits, collections.Iterable) else hits
			for item in items or ():
				self._add(item)

	def sort(self, sortOn=None):
		sortOn = sortOn or self.query.sortOn
		comparator = component.queryUtility(search_interfaces.ISearchHitComparator,
											name=sortOn)
		if comparator is not None:
			self.sorted = True
			reverse = not self.query.is_descending_sort_order
			self._hits.sort(comparator.compare, reverse=reverse)

	def __iadd__(self, other):
		if 	search_interfaces.ISearchResults.providedBy(other) or \
			search_interfaces.ISuggestAndSearchResults.providedBy(other):

			self.sorted = False
			self._hits.extend(other.hits)
			self._ihitmeta += other._ihitmeta

		return self

@interface.implementer(search_interfaces.ISuggestResults,
					   zmime_interfaces.IContentTypeAware)
class _SuggestResults(_BaseSearchResults):

	__metaclass__ = _MetaSearchResults

	def __init__(self, query):
		super(_SuggestResults, self).__init__(query)
		self._words = set()

	def get_hits(self):
		"""
		The suggested words, sorted alphabetically. Immutable.
		"""
		return sorted(self._words)

	hits = property(get_hits)
	suggestions = hits

	def add_suggestions(self, items):
		items = [items] if isinstance(items, six.string_types) or \
						   not isinstance(items, collections.Iterable) else items
		for item in items or ():
			if isinstance(item, six.string_types):
				self._words.add(unicode(item))

	add = add_suggestions

	def __iadd__(self, other):
		if 	search_interfaces.ISuggestResults.providedBy(other) or \
			search_interfaces.ISuggestAndSearchResults.providedBy(other):
			self._words.update(other.suggestions)
		return self

@interface.implementer(search_interfaces.ISuggestAndSearchResults)
class _SuggestAndSearchResults(_SearchResults, _SuggestResults):

	__metaclass__ = _MetaSearchResults

	def __init__(self, query):
		_SearchResults.__init__(self, query)
		_SuggestResults.__init__(self, query)

	def get_hits(self):
		return self._hits

	hits = property(get_hits)

	def get_words(self):
		"""
		The suggested words, sorted alphabetically. Immutable.
		"""
		return sorted(self._words)

	suggestions = property(get_words)

	def add(self, items):
		_SearchResults.add(self, items)

	def __iadd__(self, other):
		_SearchResults.__iadd__(self, other)
		_SuggestResults.__iadd__(self, other)
		return self

@interface.implementer(search_interfaces.ISearchResultsCreator)
class _SearchResultCreator(object):

	def __call__(self, query):
		return _SearchResults(query)

@interface.implementer(search_interfaces.ISuggestResultsCreator)
class _SuggestResultsCreator(object):

	def __call__(self, query):
		return _SuggestResults(query)

@interface.implementer(search_interfaces.ISuggestAndSearchResultsCreator)
class _SuggestAndSearchResultsCreator(object):

	def __call__(self, query):
		return _SuggestAndSearchResults(query)

# sort

def sort_hits(hits, reverse=False, sortOn=None):
	comparator = component.queryUtility(search_interfaces.ISearchHitComparator,
										name=sortOn) if sortOn else None
	if comparator is not None:
		if reverse:
			comparator = lambda x, y: comparator(y, x)
		return isorted(hits, comparator)
	else:
		iterator = reverse(hits) if reverse else iter(hits)
		return iterator

# legacy results

def empty_search_results(query):
	result = component.getUtility(search_interfaces.ISearchResultsCreator)(query)
	return result

def empty_suggest_and_search_results(query):
	result = component.getUtility(
						search_interfaces.ISuggestAndSearchResultsCreator)(query)
	return result

def empty_suggest_results(query):
	result = component.getUtility(search_interfaces.ISuggestResultsCreator)(query)
	return result

def _preflight(a, b):
	if a is None and b is None:
		result = (None, True)
	elif a is None and b is not None:
		result = (b, True)
	elif a is not None and b is None:
		result = (a, True)
	else:
		result = (None, False)
	return result

def _merge(a, b):
	a += b
	for k, vb in b.__dict__.items():
		if not k.startswith('_'):
			va = a.__dict__.get(k, None)
			if vb != va:
				a.__dict__[k] = vb
	return a

def merge_search_results(a, b):
	v, t = _preflight(a, b)
	if t: return v
	return _merge(a, b)

def merge_suggest_and_search_results(a, b):
	v, t = _preflight(a, b)
	if t: return v
	return _merge(a, b)

def merge_suggest_results(a, b):
	v, t = _preflight(a, b)
	if t: return v
	return _merge(a, b)
