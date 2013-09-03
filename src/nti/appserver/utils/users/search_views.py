#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
User search views.

$Id: export_views.py 23778 2013-08-29 20:38:14Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time
import collections

from pyramid.view import view_config
from pyramid import httpexceptions as hexc
from pyramid.security import authenticated_userid

import ZODB

from nti.contentsearch import common
from nti.contentsearch import constants
from nti.contentsearch import utils as search_utils
from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch import _discriminators as discriminators

from nti.dataserver import users
from nti.dataserver import authorization as nauth

from nti.externalization.datastructures import LocatedExternalDict

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

def _do_content_reindex(entity, predicate):
	t = time.time()
	countermap = collections.defaultdict(int)
	for e, obj in search_utils.find_all_indexable_pairs(entity, predicate):
		try:
			rim = search_interfaces.IRepozeEntityIndexManager(e, None)
			catalog = rim.get_create_catalog(obj) if rim is not None else None
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
	values = CaseInsensitiveDict(request.params)
	username = values.get('username', authenticated_userid(request))
	user = users.User.get_user(username)
	if not user:
		raise hexc.HTTPNotFound(detail='User not found')

	mime_types = values.get('mime_types', values.get('mimeTypes'))
	mime_types = _parse_mime_types(mime_types)
	content_types = {common.get_type_from_mimetype(x) for x in mime_types}
	content_types.discard(None)

	if not content_types:
		predicate = None  # ALL
	else:
		predicate = lambda x:False
		for t in content_types:
			f = _func_map.get(t)
			predicate = _combine_predicate(predicate, f) if f else predicate

	countermap, elapsed = _do_content_reindex(user, predicate)
	result = LocatedExternalDict()
	result['Elapsed'] = elapsed
	result['Items'] = dict(countermap)
	return result
