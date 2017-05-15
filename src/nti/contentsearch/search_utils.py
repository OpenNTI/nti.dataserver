#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import re
import six
import time

from zope import component

from nti.base._compat import text_

from nti.common.string import is_true

from nti.contentprocessing import get_content_translation_table

from nti.contentsearch.content_utils import get_collection_root_ntiid

from nti.contentsearch.interfaces import ISearchQuery
from nti.contentsearch.interfaces import ISearchPackageResolver

from nti.contentsearch.search_query import QueryObject
from nti.contentsearch.search_query import DateTimeRange

from nti.dataserver.users import User

from nti.ntiids.ntiids import ROOT
from nti.ntiids.ntiids import TYPE_OID
from nti.ntiids.ntiids import is_ntiid_of_type

_extractor_pe = re.compile(r'[?*]*(.*)')


def clean_search_query(query, language=u'en'):
    temp = re.sub(r'[*?]', '', query)
    result = text_(query) if temp else u''
    if result:
        m = _extractor_pe.search(result)
        result = m.group() if m else u''

    table = get_content_translation_table(language)
    result = result.translate(table) if result else u''
    result =text_(result)

    # auto complete phrase search
    if result.startswith('"') and not result.endswith('"'):
        result += '"'
    elif result.endswith('"') and not result.startswith('"'):
        result = '"' + result

    return result


accepted_keys = {'ntiid', 'accept',
                 'createdAfter', 'createdBefore',
                 'modifiedAfter', 'modifiedBefore'}


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

    if result is not None:
        if result.endTime is None:
            result.endTime = time.time()
        if result.startTime is None:
            result.startTime = 0
        if result.endTime < result.startTime:
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


def create_queryobject(username, params, clazz=QueryObject):
    username = username or params.get('username', None)

    context = {}

    # parse params:
    args = dict(params)
    for name in list(args.keys()):
        if name not in ISearchQuery and name not in accepted_keys:
            value = args[name]
            if value is not None:
                if isinstance(value, six.string_types):
                    value = text_(value)
                context[text_(name)] = value
            del args[name]
    # remove to be resetted
    for name in ('ntiid', 'term', 'username'):
        args.pop(name, None)

    args['context'] = context

    term = params.get('term', u'')
    term = clean_search_query(text_(term))
    args['term'] = term

    args['username'] = username
    packages = args['packages'] = list()

    ntiid = args['origin'] = params.get('ntiid', None)
    if ntiid != ROOT:
        package_ntiids = _resolve_package_ntiids(username, ntiid)
        if package_ntiids:
            for pid in package_ntiids:
                root_ntiid = get_collection_root_ntiid(pid)
                if root_ntiid is not None:
                    packages.append(root_ntiid)
    args['packages'] = sorted(set(args['packages']))  # predictable order

    accept = args.pop('accept', None)
    if accept:
        accept = set(accept.split(','))
        if '*/*' not in accept:
            accept.discard('')
            accept.discard(None)
            args['searchOn'] = sorted(accept)

    creationTime = _parse_dateRange(args, ('createdAfter', 'createdBefore',))
    modificationTime = _parse_dateRange(args,
                                        ('modifiedAfter', 'modifiedBefore'))

    args['creationTime'] = creationTime
    args['modificationTime'] = modificationTime
    args['applyHighlights'] = is_true(args.get('applyHighlights', True))

    # ILastModified fields
    if creationTime is not None and 'createdTime' not in context:
        context[u'createdTime'] = (creationTime.startTime, creationTime.endTime)
    if modificationTime is not None and 'lastModified' not in context:
        context[u'lastModified'] = (modificationTime.startTime,
                                   modificationTime.endTime)

    result = clazz(**args)
    return result
