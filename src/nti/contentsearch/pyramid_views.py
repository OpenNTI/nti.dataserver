# -*- coding: utf-8 -*-
"""
Search pyramid views.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import

logger = __import__('logging').getLogger(__name__)

import re

from zope import component
from zope import interface
from zope.location import locate

import pyramid.httpexceptions as hexc
from pyramid.security import authenticated_userid

from . import constants
from .common import sort_search_types
from .interfaces import IIndexManager
from ._search_query import QueryObject
from ._views_utils import get_collection
from .common import get_type_from_mimetype
from ._content_utils import get_content_translation_table

class BaseView(object):

	name = None

	def __init__(self, request):
		self.request = request

	@property
	def query(self):
		return get_queryobject(self.request)

	@property
	def indexmanager(self):
		return self.request.registry.getUtility(IIndexManager)

	def _locate(self, obj, parent):
		# TODO: (Instead of modification info, we should be using etags here, anyway).
		locate(obj, parent, self.name)
		# TODO: Make cachable?
		from nti.appserver import interfaces as app_interfaces  # Avoid circular imports
		interface.alsoProvides(obj, app_interfaces.IUncacheableInResponse)
		return obj

class SearchView(BaseView):

	name = 'Search'

	def __call__(self):
		query = self.query
		result = self.indexmanager.search(query=query)
		result = self._locate(result, self.request.root)
		return result

Search = SearchView

class UserDataSearchView(BaseView):

	name = 'UserSearch'

	def __call__(self):
		query = self.query
		result = self.indexmanager.search(query=query)
		result = self._locate(result, self.request.root)
		return result

UserSearch = UserDataSearchView

_extractor_pe = re.compile('[?*]*(.*)')

def clean_search_query(query, language='en'):
	temp = re.sub('[*?]', '', query)
	result = unicode(query) if temp else u''
	if result:
		m = _extractor_pe.search(result)
		result = m.group() if m else u''

	table = get_content_translation_table(language)
	result = result.translate(table) if result else u''
	result = unicode(result)

	# auto complete phrase search
	if result.startswith('"') and not result.endswith('"'):
		result += '"'
	elif result.endswith('"') and not result.startswith('"'):
		result = '"' + result

	return result

#### from IPython.core.debugger import Tracer; Tracer()() #####

indexable_type_names = frozenset(constants.indexable_type_names)

def create_queryobject(username, params, matchdict, registry=component):
	# parse params:
	args = dict(params)

	term = matchdict.get('term', u'')
	term = clean_search_query(unicode(term))
	args['term'] = term

	args['username'] = username

	ntiid = matchdict.get('ntiid', None)
	accept = args.pop('accept', None)
	exclude = args.pop('exclude', None)
	if ntiid:
		# make sure we register the location where the search query is being made
		args['location'] = ntiid
		indexid = get_collection(ntiid, registry)
		if indexid is None:
			logger.debug("Could not find collection for ntiid '%s'" % ntiid)
		else:
			args['indexid'] = indexid
	if accept:
		aset = set(accept.split(','))
		if '*/*' not in aset:
			aset = {get_type_from_mimetype(e) for e in aset}
			aset.discard(None)
			aset = aset if aset else (constants.invalid_type_,)
			args['searchOn'] = sort_search_types(aset)
	elif exclude:
		eset = set(exclude.split(','))
		if '*/*' in eset:
			args['searchOn'] = (constants.invalid_type_,)
		else:
			eset = {get_type_from_mimetype(e) for e in eset}
			eset.discard(None)
			args['searchOn'] = sort_search_types(indexable_type_names - eset)

	batchSize = args.get('batchSize', None)
	batchStart = args.get('batchStart', None)
	if batchSize is not None and batchStart is not None:
		try:
			batchSize = int(batchSize)
			batchStart = int(batchStart)
		except ValueError:
			raise hexc.HTTPBadRequest()
		if batchSize <= 0 or batchStart < 0:
			raise hexc.HTTPBadRequest()

	return QueryObject(**args)

def get_queryobject(request):
	username = request.matchdict.get('user', None)
	username = username or authenticated_userid(request)
	return create_queryobject(username, request.params, request.matchdict, request.registry)
