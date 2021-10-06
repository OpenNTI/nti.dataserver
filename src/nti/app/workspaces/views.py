#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views relating to working with invitations.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid.view import view_config

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.view_mixins import BatchingUtilsMixin

from nti.appserver.workspaces.interfaces import ICatalogCollection

from nti.dataserver import authorization as nauth

from nti.externalization import to_external_object

from nti.externalization.interfaces import StandardExternalFields

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL

logger = __import__('logging').getLogger(__name__)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ICatalogCollection,
             permission=nauth.ACT_READ,
             request_method='GET')
class CatalogCollectionView(AbstractAuthenticatedView,
                            BatchingUtilsMixin):
    """
    A generic :class:`ICatalogCollection` view that supports paging on the
    collection.
    """

    #: To maintain BWC; disable paging by default.
    _DEFAULT_BATCH_SIZE = None
    _DEFAULT_BATCH_START = None

    def __call__(self):
        result = to_external_object(self.context)
        result[TOTAL] = len(result[ITEMS])
        self._batch_items_iterable(result, result[ITEMS])
        return result


