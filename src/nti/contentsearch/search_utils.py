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

accepted_keys = {'ntiid', 'accept', 'exclude'}

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

def construct_queryobject(request):
	username = request.matchdict.get('user', None)
	username = username or request.authenticated_userid
	result = create_queryobject(username, request.params, request.matchdict)
	return result
