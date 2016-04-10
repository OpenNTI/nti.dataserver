#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import re
from urllib import quote
from urllib import unquote
from urlparse import urljoin

from zope import component

from zope.intid.interfaces import IIntIds

from pyramid.threadlocal import get_current_request

from plone.namedfile.interfaces import INamed as IPloneNamed

from nti.app.contentfolder import CFIO

from nti.common.integer_strings import to_external_string
from nti.common.integer_strings import from_external_string

from nti.contentfile.interfaces import IContentBaseFile

pattern = re.compile('(.+)/%s/(.+)(\/.*)?' % CFIO, re.UNICODE | re.IGNORECASE)

def get_ds2(request=None):
	request = request if request else get_current_request()
	try:
		result = request.path_info_peek() if request else None  # e.g. /dataserver2
	except AttributeError:  # in unit test we may see this
		result = None
	return result or "dataserver2"

def is_cf_io_href(link):
	return bool(pattern.match(unquote(link)))

def safe_download_file_name(name):
	if not name:
		result = 'file.dat'
	else:
		ext = os.path.splitext(name)[1]
		try:
			result = quote(name)
		except Exception:
			result = 'file' + ext
	return result

def to_external_cf_io_href(context, request=None):
	context = IContentBaseFile(context, None)
	intids = component.getUtility(IIntIds)
	safe_name = safe_download_file_name(context.filename)
	uid = intids.queryId(context) if context is not None else None
	ds2 = get_ds2(request)
	if ds2 and uid is not None:
		code = to_external_string(uid)
		href = '/%s/%s/%s/%s' % (ds2, CFIO, code, safe_name)
		return href
	return None
get_cf_io_href = to_external_cf_io_href

def to_external_cf_io_url(context, request=None):
	request = request if request else get_current_request()
	href = to_external_cf_io_href(context, request=request)
	result = urljoin(request.host_url, href) if href else href
	return result
get_cf_io_url = to_external_cf_io_url

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
