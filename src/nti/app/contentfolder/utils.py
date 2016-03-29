#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import re
from urllib import unquote
from urlparse import urljoin

from zope import component

from zope.intid.interfaces import IIntIds

from pyramid.threadlocal import get_current_request

from plone.namedfile.interfaces import INamed as IPloneNamed

from nti.app.contentfolder import CFIO

from nti.contentfile.interfaces import IContentBaseFile

from nti.externalization.integer_strings import to_external_string
from nti.externalization.integer_strings import from_external_string

pattern = re.compile('(.+)/%s/(.+)(\/.*)?' % CFIO, re.UNICODE | re.IGNORECASE)

def get_ds2(request=None):
	request = request if request else get_current_request()
	try:
		result = request.path_info_peek() if request else None # e.g. /dataserver2
	except AttributeError:  # in unit test we may see this
		result = None
	return result or "dataserver2"

def is_cf_io_href(link):
	return bool(pattern.match(unquote(link)))

def get_cf_io_href(context, request=None):
	context = IContentBaseFile(context, None)
	intids = component.getUtility(IIntIds)
	uid = intids.queryId(context) if context is not None else None
	ds2 = get_ds2(request)
	if ds2 and uid is not None:
		name = to_external_string(uid)
		href = '/%s/%s/%s' % (ds2, CFIO, name)
		return href
	return None

def get_cf_io_url(context, request=None):
	request = request if request else get_current_request()
	href = get_cf_io_href(context, request=request)
	result = urljoin(request.host_url, href) if href else href
	return result

def get_object(uid, intids=None):
	intids = component.getUtility(IIntIds) if intids is None else intids
	result = intids.queryObject(uid)
	return result

def get_file_from_cf_io_url(link, intids=None):
	result = None
	try:
		link = unquote(link)
		if is_cf_io_href(link):
			match = pattern.match(link)
			uid = match.groups()[1]
			if '/' in uid:
				uid = uid.split('/')[0]
			uid = from_external_string(uid)
			result = get_object(uid, intids=intids)
			if not IPloneNamed.providedBy(result):
				result = None
	except Exception:
		logger.error("Error while getting file from %s", link)
	return result
