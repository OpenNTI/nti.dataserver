#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Search utils.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import re
import gevent
import functools

from zope import component

from pyramid import httpexceptions as hexc
from pyramid.threadlocal import get_current_request

from nti.contentlibrary.interfaces import IContentPackageBundle

from nti.dataserver.interfaces import IDataserverTransactionRunner

from nti.ntiids.ntiids import TYPE_OID
from nti.ntiids.ntiids import is_ntiid_of_type
from nti.ntiids.ntiids import find_object_with_ntiid

from .common import sort_search_types
from .common import get_indexable_types
from .common import get_type_from_mimetype

from .constants import invalid_type_

from .content_utils import get_collection_root
from .content_utils import get_content_translation_table

from .interfaces import ISearchQuery
from .interfaces import IIndexManager

from .search_query import QueryObject
from .search_query import DateTimeRange

def gevent_spawn(request=None, side_effect_free=True, func=None, **kwargs):
	assert func is not None

	# prepare function call
	new_callable = functools.partial(func, **kwargs)

	# save site names  / deprecated
	request = request if request is not None else get_current_request()
	site_names = getattr(request, 'possible_site_names', ()) or ('',)

	def _runner():
		transactionRunner = component.getUtility(IDataserverTransactionRunner)
		transactionRunner = functools.partial(transactionRunner,
											  site_names=site_names,
											  side_effect_free=side_effect_free)
		transactionRunner(new_callable)

	# user the avaible spawn function
	greenlet = 	request.nti_gevent_spawn(run=_runner) if request is not None \
				else gevent.spawn(_runner)

	return greenlet

def register_content(package=None, indexname=None, indexdir=None, ntiid=None, indexmanager=None):
	indexmanager = indexmanager or component.queryUtility(IIndexManager)
	if package is None:
		assert indexname, 'must provided and index name'
		assert indexdir, 'must provided and index location directory'
		ntiid = ntiid or indexname
	else:
		ntiid = ntiid or package.ntiid
		indexdir = indexdir or package.make_sibling_key('indexdir').absolute_path
		indexname = os.path.basename(package.get_parent_key().absolute_path) # TODO: So many assumptions here

	if indexmanager is None:
		return

	try:
		__traceback_info__ = indexdir, indexmanager, indexname, ntiid
		if indexmanager.register_content(indexname=indexname, indexdir=indexdir, ntiid=ntiid):
			logger.debug('Added index %s at %s to indexmanager', indexname, indexdir)
		else:
			logger.warn('Failed to add index %s at %s to indexmanager', indexname, indexdir)
	except ImportError: # pragma: no cover
		# Adding a book on disk loads the Whoosh indexes, which
		# are implemented as pickles. Incompatible version changes
		# lead to unloadable pickles. We've seen this manifest as ImportError
		logger.exception("Failed to add book search %s", indexname)

_extractor_pe = re.compile('[?*]*(.*)')

def is_true(v):
	return v is not None and str(v).lower() in ('1', 'true', 'yes', 'y', 't')

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

accepted_keys = {'ntiid', 'accept', 'exclude', 'createdAfter', 'createdBefore',
				 'modifiedAfter', 'modifiedBefore'}

def get_batch_size_start(params):
	batch_size = params.get('batchSize', None)
	batch_start = params.get('batchStart', None)
	if batch_size is not None and batch_start is not None:
		try:
			batch_size = int(batch_size)
			batch_start = int(batch_start)
		except ValueError:
			raise hexc.HTTPBadRequest()
		if batch_size <= 0 or batch_start < 0:
			raise hexc.HTTPBadRequest()
	else:
		batch_size = batch_start = None
	return batch_size, batch_start

def check_time(value):
	try:
		value = float(value)
	except ValueError:
		raise hexc.HTTPBadRequest()
	if value < 0:
		raise hexc.HTTPBadRequest()
	return value

def _parse_dateRange(args, fields):
	result = None
	for idx, name in enumerate(fields):
		value = args.pop(name, None)
		value = check_time(value) if value is not None else None
		if value is not None:
			result = result or DateTimeRange()
			if idx == 0: #after
				result.startTime = value
			else:  # before
				result.endTime = value

	if 	result is not None and result.endTime is not None and \
		result.startTime is not None and result.endTime < result.startTime:
		raise hexc.HTTPBadRequest()
	return result

def _is_type_oid(ntiid):
	return is_ntiid_of_type(ntiid, TYPE_OID)

def _resolve_package_ntiids(ntiid):
	result = []
	if ntiid:
		if _is_type_oid(ntiid):
			obj = find_object_with_ntiid(ntiid)
			bundle = IContentPackageBundle(obj, None)
			if bundle is not None and bundle.ContentPackages:
				result = [x.ntiid for x in bundle.ContentPackages]
		else:
			result = [ntiid]
	return result

def create_queryobject(username, params, matchdict):
	indexable_type_names = get_indexable_types()
	username = username or matchdict.get('user', None)

	# parse params:
	args = dict(params)
	for name in list(args.keys()):
		if name not in ISearchQuery and name not in accepted_keys:
			del args[name]

	term = matchdict.get('term', u'')
	term = clean_search_query(unicode(term))
	args['term'] = term

	args['username'] = username
	packages = args['packages'] = list()

	ntiid = matchdict.get('ntiid', None)
	package_ntiids = _resolve_package_ntiids(ntiid)
	if package_ntiids:
		# predictable order for digest
		package_ntiids.sort()
		# make sure we register the location where the search query is being made
		args['location'] = ntiid if not _is_type_oid(ntiid) else package_ntiids[0]
		for pid in package_ntiids:
			root = get_collection_root(pid)
			if root is not None:
				root_ntiid = root.ntiid
				packages.append(root_ntiid)
				if 'indexid' not in args: # legacy
					args['indexid'] = root_ntiid
			else:
				logger.debug("Could not find collection for ntiid '%s'" % pid)

	accept = args.pop('accept', None)
	exclude = args.pop('exclude', None)
	if accept:
		aset = set(accept.split(','))
		if '*/*' not in aset:
			aset = {get_type_from_mimetype(e) for e in aset}
			aset.discard(None)
			aset = aset if aset else (invalid_type_,)
			args['searchOn'] = sort_search_types(aset)
	elif exclude:
		eset = set(exclude.split(','))
		if '*/*' in eset:
			args['searchOn'] = (invalid_type_,)
		else:
			eset = {get_type_from_mimetype(e) for e in eset}
			eset.discard(None)
			args['searchOn'] = sort_search_types(indexable_type_names - eset)

	args['batchSize'], args['batchStart'] = get_batch_size_start(args)

	creationTime = _parse_dateRange(args, ('createdAfter', 'createdBefore',))
	modificationTime = _parse_dateRange(args, ('modifiedAfter', 'modifiedBefore'))

	args['creationTime'] = creationTime
	args['modificationTime'] = modificationTime
	args['applyHighlights'] = is_true(args.get('applyHighlights', True))

	return QueryObject(**args)

def construct_queryobject(request):
	username = request.matchdict.get('user', None)
	username = username or request.authenticated_userid
	result = create_queryobject(username, request.params, request.matchdict)
	return result
