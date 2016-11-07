#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Search utils.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import re

from zope import component

from nti.common.string import is_true
from nti.common.string import to_unicode

from nti.dataserver.users import User

from nti.ntiids.ntiids import TYPE_OID
from nti.ntiids.ntiids import is_ntiid_of_type

from nti.contentsearch.constants import invalid_type_

from nti.contentsearch.content_utils import get_collection_root
from nti.contentsearch.content_utils import get_content_translation_table

from nti.contentsearch.interfaces import ISearchQuery
from nti.contentsearch.interfaces import ISearchPackageResolver

from nti.contentsearch.search_query import QueryObject
from nti.contentsearch.search_query import DateTimeRange

def _get_current_request():
	result = None
	try:
		from pyramid.threadlocal import get_current_request
		result = get_current_request()
	except ImportError:
		pass
	return result

def _get_site_names(query=None):
	result =  getattr(query, 'site_names', None) 
	if result is None:
		request = _get_current_request()
		result = getattr(request, 'possible_site_names', None)
	return  ('',) if not result else result 

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

accepted_keys = {'ntiid', 'accept', 'exclude', 
				 'createdAfter', 'createdBefore',
				 'modifiedAfter', 'modifiedBefore'}

def get_batch_size_start(params):
	batch_size = params.get('batchSize', None)
	batch_start = params.get('batchStart', None)
	if batch_size is not None and batch_start is not None:
		try:
			batch_size = int(batch_size)
			batch_start = int(batch_start)
		except ValueError:
			raise ValueError("Invalid batch size/start")
		if batch_size <= 0 or batch_start < 0:
			raise ValueError("Invalid batch size/start")
	else:
		batch_size = batch_start = None
	return batch_size, batch_start

def check_time(value):
	value = float(value)
	if value < 0:
		raise ValueError("Invalid time float")
	return value

def _parse_dateRange(args, fields):
	result = None
	for idx, name in enumerate(fields):
		value = args.pop(name, None)
		value = check_time(value) if value is not None else None
		if value is not None:
			result = result or DateTimeRange()
			if idx == 0:  # after
				result.startTime = value
			else:  # before
				result.endTime = value

	if 	result is not None and result.endTime is not None and \
		result.startTime is not None and result.endTime < result.startTime:
		raise ValueError("Invalid time interval")
	return result

def _is_type_oid(ntiid):
	return bool(is_ntiid_of_type(ntiid, TYPE_OID))

def _resolve_package_ntiids(username, ntiid=None):
	result = set()
	if ntiid:
		user = User.get_user(username)
		for resolver in component.subscribers((user,), ISearchPackageResolver):
			ntiids = resolver.resolve(user, ntiid)
			result.update(ntiids or ())
	return sorted(result)  # predictable order for digest

def create_queryobject(username, params):
	indexable_type_names = get_indexable_types()
	username = username or params.get('username', None)

	context = {}

	# parse params:
	args = dict(params)
	for name in list(args.keys()):
		if name not in ISearchQuery and name not in accepted_keys:
			value = args[name]
			if value:
				context[to_unicode(name)] = to_unicode(value)
			del args[name]
	# remove to be resetted
	for name in ('ntiid', 'term', 'username'):
		args.pop(name, None)

	args['context'] = context

	term = params.get('term', u'')
	term = clean_search_query(to_unicode(term))
	args['term'] = term

	args['username'] = username
	packages = args['packages'] = list()

	ntiid = params.get('ntiid', None)
	args['origin'] = ntiid

	package_ntiids = _resolve_package_ntiids(username, ntiid)
	if package_ntiids:
		# make sure we register the location where the search query is being made
		args['location'] = package_ntiids[0] if _is_type_oid(ntiid) else ntiid
		for pid in package_ntiids:
			root = get_collection_root(pid)
			if root is not None:
				root_ntiid = root.ntiid
				packages.append(root_ntiid)
			else:
				logger.debug("Could not find collection for ntiid '%s'" % pid)
	elif ntiid:
		args['location'] = ntiid

	args['packages'] = sorted(set(args['packages']))  # predictable order

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
