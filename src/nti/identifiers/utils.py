#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component

from zope.component.hooks import getSite

from zope.intid.interfaces import IIntIds

from nti.coremetadata.interfaces import IUser

from nti.identifiers.index import IX_SITE
from nti.identifiers.index import IX_EXTERNAL_IDS
from nti.identifiers.index import IX_EXTERNAL_TYPES

from nti.identifiers.index import get_identifier_catalog

from nti.identifiers.interfaces import IUserExternalIdentityContainer
from nti.identifiers.interfaces import IUserExternalIdentityValidator

from nti.site.site import get_component_hierarchy_names

logger = __import__('logging').getLogger(__name__)


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


def get_external_identifiers(user):
    """
    Fetches a dict (external_type:external_id) of external identifiers for
    this user in this site.
    """
    identity_container = IUserExternalIdentityContainer(user)
    result = {}
    if identity_container:
        current_site = getSite()
        current_site_names = get_component_hierarchy_names(current_site)
        if      identity_container.site_name \
            and identity_container.site_name in current_site_names:
            # Identity site_name must be in hierarchy of current sites.
            result = dict(identity_container)
        elif    not identity_container.site_name \
            and not current_site_names:
            # No current site and no identity site name (testing)
            result = dict(identity_container)
    return result


def _is_valid(user, external_type, external_id):
    # pylint: disable=too-many-function-args
    validator = IUserExternalIdentityValidator(user)
    return validator.is_valid(external_type, external_id)


def get_user_for_external_id(external_type, external_id):
    """
    Find any user associated with the given external id and external_type, for
    any site in this site hierarchy.
    """
    result = None
    if external_id is None or external_type is None:
        return result
    catalog = get_identifier_catalog()
    intids = component.getUtility(IIntIds)
    site_names = get_component_hierarchy_names()
    # Only query for lowercase, since that's how we store them.
    query = {
        IX_EXTERNAL_IDS: {'any_of': (external_id.lower(),)},
        IX_EXTERNAL_TYPES: {'any_of': (external_type.lower(),)}
    }
    if site_names:
        query[IX_SITE] = {'any_of': site_names}
    for uid in catalog.apply(query) or ():
        # We store collections of a users' external_ids and external_types
        # instead of the one-to-one relationship between a external_type and
        # external_id; therefore, we must validate that the found user has the
        # requested mapping from external_type->external_id to avoid collisions
        # between sites.
        user = intids.queryObject(uid)
        if      IUser.providedBy(user) \
            and _is_valid(user, external_type, external_id):
            result = user
            break
    return result
