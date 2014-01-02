# -*- coding: utf-8 -*-
"""
Search pyramid views.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import re
import time

from zope import component
from zope import interface
from zope.event import notify
from zope.location import locate

from pyramid import httpexceptions as hexc

from nti.dataserver.users import Entity

from . import common
from . import constants
from . import search_query
from . import content_utils
from . import interfaces as search_interfaces

_extractor_pe = re.compile('[?*]*(.*)')

def clean_search_query(query, language='en'):
	temp = re.sub('[*?]', '', query)
	result = unicode(query) if temp else u''
	if result:
		m = _extractor_pe.search(result)
		result = m.group() if m else u''

	table = content_utils.get_content_translation_table(language)
	result = result.translate(table) if result else u''
	result = unicode(result)

	# auto complete phrase search
	if result.startswith('"') and not result.endswith('"'):
		result += '"'
	elif result.endswith('"') and not result.startswith('"'):
		result = '"' + result

	return result

#### from IPython.core.debugger import Tracer; Tracer()() #####

accepted_keys = {'ntiid', 'accept', 'exclude'}
indexable_type_names = frozenset(constants.indexable_type_names)

def create_queryobject(username, params, matchdict, registry=component):
	# parse params:
	args = dict(params)
	for name in list(args.keys()):
		if name not in search_interfaces.ISearchQuery and name not in accepted_keys:
			del args[name]
	
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
		indexid = content_utils.get_collection_root_ntiid(ntiid, registry=registry)
		if indexid is None:
			logger.debug("Could not find collection for ntiid '%s'" % ntiid)
		else:
			args['indexid'] = indexid
	if accept:
		aset = set(accept.split(','))
		if '*/*' not in aset:
			aset = {common.get_type_from_mimetype(e) for e in aset}
			aset.discard(None)
			aset = aset if aset else (constants.invalid_type_,)
			args['searchOn'] = common.sort_search_types(aset)
	elif exclude:
		eset = set(exclude.split(','))
		if '*/*' in eset:
			args['searchOn'] = (constants.invalid_type_,)
		else:
			eset = {common.get_type_from_mimetype(e) for e in eset}
			eset.discard(None)
			args['searchOn'] = common.sort_search_types(indexable_type_names - eset)

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

	return search_query.QueryObject(**args)

def get_queryobject(request):
	username = request.matchdict.get('user', None)
	username = username or request.authenticated_userid
	return create_queryobject(username, request.params, request.matchdict,
							  request.registry)

class BaseView(object):

	name = None

	def __init__(self, request):
		self.request = request

	@property
	def query(self):
		return get_queryobject(self.request)

	@property
	def indexmanager(self):
		return self.request.registry.getUtility(search_interfaces.IIndexManager)

	def _locate(self, obj, parent):
		# TODO: (Instead of modification info, we should be using etags here, anyway).
		locate(obj, parent, self.name)
		# TODO: Make cachable?
		from nti.appserver import interfaces as app_interfaces  # Avoid circular imports
		interface.alsoProvides(obj, app_interfaces.IUncacheableInResponse)
		return obj

	def search(self, query):
		now = time.time()
		result = self.indexmanager.search(query=query)
		metadata = result.metadata
		elapsed = time.time() - now
		entity = Entity.get_entity(query.username)
		notify(search_interfaces.SearchCompletedEvent(entity, query, metadata, elapsed))
		return result

	def __call__(self):
		query = self.query
		result = self.search(query=query)
		result = self._locate(result, self.request.root)
		return result

class SearchView(BaseView):
	name = 'Search'
Search = SearchView  # BWC

class UserDataSearchView(BaseView):
	name = 'UserSearch'
UserSearch = UserDataSearchView  # BWC
