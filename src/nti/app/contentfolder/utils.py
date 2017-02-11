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
import time
from urllib import quote
from urllib import unquote
from urlparse import urljoin
from datetime import datetime

from slugify import slugify_filename

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
        # e.g. /dataserver2
        result = request.path_info_peek() if request else None
    except AttributeError:  # in unit test we may see this
        result = None
    return result or u"dataserver2"


def is_cf_io_href(link):
    return bool(pattern.match(unquote(link))) if link else False


def safe_download_file_name(name):
    if not name:
        result = u'file.dat'
    else:
        ext = os.path.splitext(name)[1]
        try:
            result = quote(name)
        except Exception:
            result = u'file' + ext
    return result


def to_external_cf_io_href(context, request=None):
    ds2 = get_ds2(request)
    intids = component.getUtility(IIntIds)
    context = IContentBaseFile(context, None)
    if context is not None:
        safe_name = safe_download_file_name(context.filename)
        uid = intids.queryId(context) if context is not None else None
        if ds2 and uid is not None:
            code = to_external_string(uid)
            href = u'/%s/%s/%s/%s' % (ds2, CFIO, code, safe_name)
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
    __traceback_info__ = link,
    result = None
    try:
        link = unquote(link)
        if is_cf_io_href(link):
            match = pattern.match(link)
            uid = match.groups()[1]
            uid = uid.split('/')[0] if '/' in uid else uid
            uid = from_external_string(uid)
            result = get_object(uid, intids=intids)
            if not IPloneNamed.providedBy(result):
                result = None
    except Exception:
        logger.error("Error while getting file from %s", link)
    return result


def get_unique_file_name(name, container, now=None, filename=None):
    counter = 0
    hex_key = 0
    newtext = name
    filename = filename or name
    slugified = slugify_filename(name)
    text_noe, ext = os.path.splitext(slugified)
    now = now or time.time()  # current time
    now = datetime.fromtimestamp(now).strftime("%H.%M.%S")
    while True:
        if newtext not in container:
            break
        else:
            counter += 1
            hex_key = "%s.%s" % (now, counter)
            newtext = "%s.%s%s" % (text_noe, hex_key, ext)

    if hex_key:
        fn_noe, ext = os.path.splitext(filename)
        filename = "%s.%s%s" % (fn_noe, hex_key, ext)

    return newtext, filename
