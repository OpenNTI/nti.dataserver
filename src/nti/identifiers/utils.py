#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.intid.interfaces import IIntIds

from nti.identifiers.index import IX_EXTERNAL_IDS

from nti.identifiers.index import get_identifier_catalog


def get_external_ids_for_user(user):
    """
    Fetches all external identifiers associated with user. Typically only
    useful for testing
    """
    intids = component.getUtility(IIntIds)
    uid = intids.queryId(user)
    result = ()
    if uid is not None:
        catalog = get_identifier_catalog()
        id_index = catalog[IX_EXTERNAL_IDS]
        vals = id_index.documents_to_values.get(uid)
        if vals is not None:
            result = tuple(vals)
    return result


def get_user_for_external_id(external_id):
    """
    Find any user associated with the given external id.
    """
    result = None
    if external_id is None:
        return result
    catalog = get_identifier_catalog()
    intids = component.getUtility(IIntIds)
    # Only query for lowercase, since that's how we store them.
    query = {IX_EXTERNAL_IDS: {'any_of': (external_id.lower(),)}}
    for uid in catalog.apply(query) or ():
        user = intids.queryObject(uid)
        if user is not None:
            result = user
            break
    return result
