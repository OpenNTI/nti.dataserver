#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import string
from math import floor
from urlparse import urljoin

from zope import component

from zope.intid.interfaces import IIntIds

from pyramid.threadlocal import get_current_request

from nti.app.contentfolder import CF_IO

from nti.contentfile.interfaces import IContentFile

def toBase62(num, b=62):
	if b <= 0 or b > 62:
		return 0
	base = string.digits + string.lowercase + string.uppercase
	r = num % b
	res = base[r];
	q = floor(num / b)
	while q:
		r = q % b
		q = floor(q / b)
		res = base[int(r)] + res
	return res

def toBase10(num, b=62):
	base = string.digits + string.lowercase + string.uppercase
	limit = len(num)
	res = 0
	for i in xrange(limit):
		res = b * res + base.find(num[i])
	return res

def get_ds2(request=None):
	request = request if request else get_current_request()
	try:
		return request.path_info_peek() if request else None  # e.g. /dataserver2
	except AttributeError:  # in unit test we may see this
		return None

def get_cf_ea_href(context, request=None):
	context = IContentFile(context, None)
	intids = component.getUtility(IIntIds)
	uid = intids.queryId(context) if context is not None else None
	ds2 = get_ds2(request)
	if ds2 and uid is not None:
		name = toBase62(uid)
		href = '/%s/%s/%s' % (ds2, CF_IO, name)
		return href
	return None

def get_cf_ea_url(context, request=None):
	request = request if request else get_current_request()
	href = get_cf_ea_href(context, request=request)
	result = urljoin(request.host_url, href) if href else href
	return result
