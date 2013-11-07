#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
User search views.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time
import simplejson
import collections

from pyramid.view import view_config
from pyramid import httpexceptions as hexc
from pyramid.security import authenticated_userid

import ZODB

from nti.contentsearch import common
from nti.contentsearch import constants
from nti.contentsearch import discriminators
from nti.contentsearch import utils as search_utils
from nti.contentsearch import interfaces as search_interfaces

from nti.dataserver import users
from nti.dataserver import authorization as nauth
from nti.dataserver import interfaces as nti_interfaces

from nti.externalization.datastructures import LocatedExternalDict

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.utils.maps import CaseInsensitiveDict

_func_map = {
				constants.note_: search_utils.note_predicate,
				constants.post_: search_utils.post_predicate,
				constants.highlight_: search_utils.highlight_predicate,
				constants.redaction_: search_utils.redaction_predicate,
				constants.messageinfo_: search_utils.messageinfo_predicate
			}

def _combine_predicate(new, old=None):
	if not old:
		return new
	result = lambda obj: new(obj) or old(obj)
	return result

def _parse_mime_types(value):
	mime_types = set(value.split(','))
	if '*/*' in mime_types:
		mime_types = ()
	elif mime_types:
		mime_types = {e.strip().lower() for e in mime_types}
		mime_types.discard(u'')
	return mime_types

def _remove_catalogs(entity, content_types=()):
	count = 0
	rim = search_interfaces.IRepozeEntityIndexManager(entity)
	for key in list(rim.keys()):
		if not content_types or key in content_types:
			rim.pop(key, None)
			count += 1
	return count

def _do_content_reindex(entity, predicate):
	t = time.time()
	countermap = collections.defaultdict(int)
	for e, obj in search_utils.find_all_indexable_pairs(entity, predicate):
		try:
			rim = search_interfaces.IRepozeEntityIndexManager(e)
			catalog = rim.get_create_catalog(obj)
			if catalog is not None:
				docid = discriminators.query_uid(obj)
				if docid is not None:
					catalog.index_doc(docid, obj)
					mt = common.get_mimetype_from_type(common.get_type_name(obj))
					countermap[mt] += 1
		except ZODB.POSException.POSKeyError:
			pass

	elapsed = time.time() - t
	return countermap, elapsed

@view_config(route_name='objects.generic.traversal',
			 name='reindex_content',
			 renderer='rest',
			 request_method='POST',
			 permission=nauth.ACT_MODERATE)
def reindex_content(request):
	values = simplejson.loads(unicode(request.body, request.charset)) if request.body else {}
	values = CaseInsensitiveDict(**values)
	username = values.get('username', authenticated_userid(request))
	entity = users.User.get_entity(username) or find_object_with_ntiid(username)
	if entity is None or not nti_interfaces.IEntity.providedBy(entity):
		raise hexc.HTTPNotFound(detail='Entity not found')

	mime_types = values.get('mime_types', values.get('mimeTypes'))
	mime_types = _parse_mime_types(mime_types) if mime_types else ()
	content_types = {common.get_type_from_mimetype(x) for x in mime_types}
	content_types.discard(None)

	if not content_types and not mime_types:
		predicate = None  # ALL
	else:
		predicate = lambda x:False
		for t in content_types:
			f = _func_map.get(t)
			predicate = _combine_predicate(predicate, f()) if f else predicate

	_remove_catalogs(entity, content_types)
	countermap, elapsed = _do_content_reindex(entity, predicate)
	result = LocatedExternalDict()
	result['Elapsed'] = elapsed
	result['Items'] = dict(countermap)
	return result
