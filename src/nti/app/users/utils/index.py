#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import six

from zope import component

from zope.intid.interfaces import IIntIds

from nti.app.users.index import IX_CONTEXT
from nti.app.users.index import IX_USERNAME
from nti.app.users.index import get_context_lastseen_catalog

from nti.coremetadata.interfaces import IContextLastSeenRecord

logger = __import__('logging').getLogger(__name__)


def get_context_lastseen_records(usernames=(), contexts=()):
    catalog = get_context_lastseen_catalog()
    if isinstance(usernames, six.string_types):
        usernames = usernames.split(",")
    if isinstance(contexts, six.string_types):
        contexts = contexts.split(",")

    query = {}
    result = None

    if usernames:
        query[IX_USERNAME] = {'any_of': usernames}
    if contexts:
        query[IX_CONTEXT] = {'any_of': contexts}

    if query:
        result = set()
        intids = component.getUtility(IIntIds)
        for doc_id in catalog.apply(query) or ():
            record = intids.queryObject(doc_id)
            if IContextLastSeenRecord.providedBy(record):
                result.add(record)
        result = sorted(result, reverse=True)
    return result or ()


def get_context_lastseen_timestamp(user, context):
    username = getattr(user, 'username', user)
    context = getattr(context, 'ntiid', context)
    records = get_context_lastseen_records((username,), (context,))
    return records[0].timestamp if records else None
