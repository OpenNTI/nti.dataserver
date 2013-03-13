# -*- coding: utf-8 -*-
"""
Search pyramid views.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import

logger = __import__('logging').getLogger(__name__)

import re

import pyramid.httpexceptions as hexc
from pyramid.security import authenticated_userid

from zope import interface
from zope.location import locate

from . import constants
from .interfaces import IIndexManager
from ._search_query import QueryObject
from .common import normalize_type_name
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
	return unicode(result)

#### from IPython.core.debugger import Tracer; Tracer()() #####

def get_queryobject(request):

	# parse params:
	args = dict(request.params)

	term = request.matchdict.get('term', u'')
	term = clean_search_query(unicode(term))
	args['term'] = term

	username = request.matchdict.get('user', None)
	username = username or authenticated_userid(request)
	args['username'] = username

	ntiid = request.matchdict.get('ntiid', None)
	accept = args.pop('accept', None)
	exclude = args.pop('exclude', None)
	searchOn = args.pop('searchOn', None)
	if ntiid:
		args['location'] = ntiid
		indexid = get_collection(ntiid, request.registry)
		if indexid is None:
			logger.debug("Could not find collection for ntiid '%s'" % ntiid)
		else:
			args['indexid'] = indexid
	if searchOn:
		nset = {normalize_type_name(e) for e in searchOn.split(',')}
		args['searchOn'] = nset or (constants.invalid_type_,)
	elif accept:
		aset = set(accept.split(','))
		if '*/*' not in aset:
			aset = {get_type_from_mimetype(e) for e in aset} or (constants.invalid_type_,)
			args['searchOn'] = aset
	elif exclude:
		eset = set(exclude.split(','))
		if '*/*' not in eset:
			args['searchOn'] = (constants.invalid_type_,)
		else:
			eset = {get_type_from_mimetype(e) for e in eset}
			args['searchOn'] = constants.indexable_type_names - eset

	batch_size = args.get('batchSize', None)
	batch_start = args.get('batchStart', None)
	if batch_size is not None and batch_start is not None:
		try:
			batch_size = int(batch_size)
			batch_start = int(batch_start)
		except ValueError:
			raise hexc.HTTPBadRequest()
		if batch_size <= 0 or batch_start < 0:
			raise hexc.HTTPBadRequest()

	return QueryObject(**args)
