#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Search utils.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import re

from pyramid import httpexceptions as hexc

from . import common
from . import constants
from . import search_query
from . import content_utils
from . import interfaces as search_interfaces

_extractor_pe = re.compile('[?*]*(.*)')

def is_true(v):
	return v is not None and str(v).lower() in ('1', 'true', 'yes', 'y', 't')

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
			result = result or search_query.DateTimeRange()
			if idx == 0: #after 
				result.startTime = value
			else:  # before
				result.endTime = value

	if 	result is not None and result.endTime is not None and \
		result.startTime is not None and result.endTime < result.startTime:
		raise hexc.HTTPBadRequest()
	return result

def create_queryobject(username, params, matchdict):

	indexable_type_names = common.get_indexable_types()
	username = username or matchdict.get('user', None)

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
		indexid = content_utils.get_collection_root_ntiid(ntiid)
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

	args['batchSize'], args['batchStart'] = get_batch_size_start(args)
	
	creationTime = _parse_dateRange(args, ('createdAfter', 'createdBefore',))
	modificationTime = _parse_dateRange(args, ('modifiedAfter', 'modifiedBefore'))

	args['creationTime'] = creationTime
	args['modificationTime'] = modificationTime
	args['applyHighlights'] = is_true(args.get('applyHighlights', True))

	return search_query.QueryObject(**args)

def construct_queryobject(request):
	username = request.matchdict.get('user', None)
	username = username or request.authenticated_userid
	result = create_queryobject(username, request.params, request.matchdict)
	return result
