#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid.view import view_config
from pyramid.view import view_defaults

from zope import component

from zope.intid.interfaces import IIntIds

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.users.adapters import context_lastseen_factory

from nti.app.users.index import get_context_lastseen_catalog

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IShardLayout
from nti.dataserver.interfaces import IDataserverFolder

from nti.dataserver.metadata.index import get_metadata_catalog

from nti.dataserver.users.index import get_entity_catalog
from nti.dataserver.users.index import add_catalog_filters

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

logger = __import__('logging').getLogger(__name__)


@view_config(name='RebuildEntityCatalog')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=IDataserverFolder,
               permission=nauth.ACT_NTI_ADMIN)
class RebuildEntityCatalogView(AbstractAuthenticatedView):

    def __call__(self):
        intids = component.getUtility(IIntIds)
        # clear indexes
        catalog = get_entity_catalog()
        for index in catalog.values():
            index.clear()
        # filters need to be added
        add_catalog_filters(catalog, catalog.family)
        # reindex
        count = 0
        meta_catalog = get_metadata_catalog()
        dataserver = component.getUtility(IDataserver)
        users_folder = IShardLayout(dataserver).users_folder
        # pylint: disable=no-member
        for obj in users_folder.values():
            doc_id = intids.queryId(obj)
            if doc_id is None:
                continue
            count += 1
            catalog.index_doc(doc_id, obj)
            meta_catalog.index_doc(doc_id, obj)
        result = LocatedExternalDict()
        result[ITEM_COUNT] = result[TOTAL] = count
        return result


@view_config(name='RebuildContextLastSeenCatalog')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=IDataserverFolder,
               permission=nauth.ACT_NTI_ADMIN)
class RebuildContextLastSeenCatalogView(AbstractAuthenticatedView):

    def __call__(self):
        intids = component.getUtility(IIntIds)
        # clear indexes
        catalog = get_context_lastseen_catalog()
        for index in catalog.values():
            index.clear()
        # reindex
        count = 0
        meta_catalog = get_metadata_catalog()
        dataserver = component.getUtility(IDataserver)
        users_folder = IShardLayout(dataserver).users_folder
        # pylint: disable=no-member
        for entity in users_folder.values():
            if not IUser.providedBy(entity):
                continue
            container = context_lastseen_factory(entity, False)
            if not container:
                continue
            # index records
            for record in list(container.values()):
                doc_id = intids.queryId(record)
                if doc_id is not None:
                    count += 1
                    catalog.index_doc(doc_id, record)
                    meta_catalog.index_doc(doc_id, record)
        result = LocatedExternalDict()
        result[ITEM_COUNT] = result[TOTAL] = count
        return result
