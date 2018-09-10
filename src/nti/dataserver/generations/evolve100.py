#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from zope.component.hooks import site as current_site

from zope.intid.interfaces import IIntIds

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

from nti.dataserver.metadata.index import IX_MIMETYPE
from nti.dataserver.metadata.index import IX_SHAREDWITH
from nti.dataserver.metadata.index import get_metadata_catalog

generation = 100

logger = __import__('logging').getLogger(__name__)

NEW_MIMETYPE = 'application/vnd.nextthought.meeting'
OLD_MIMETYPE = 'application/vnd.nextthought._meeting'

@interface.implementer(IDataserver)
class MockDataserver(object):

    root = None

    def get_by_oid(self, oid, ignore_creator=False):
        resolver = component.queryUtility(IOIDResolver)
        if resolver is None:
            logger.warning(
                "Using dataserver without a proper ISiteManager."
            )
        else:
            return resolver.get_object_by_oid(oid, ignore_creator=ignore_creator)
        return None


def do_evolve(context, generation=generation):  # pylint: disable=redefined-outer-name
    conn = context.connection
    ds_folder = conn.root()['nti.dataserver']

    mock_ds = MockDataserver()
    mock_ds.root = ds_folder
    component.provideUtility(mock_ds, IDataserver)

    count = 0
    with current_site(ds_folder):
        assert component.getSiteManager() == ds_folder.getSiteManager(), \
               "Hooks not installed?"

        lsm = ds_folder.getSiteManager()
        intids = lsm.getUtility(IIntIds)
        from IPython.terminal.debugger import set_trace;set_trace()
        # get catalog and indexes
        catalog = get_metadata_catalog()
        mimeType_index = catalog[IX_MIMETYPE]
        sharedWith_index = catalog[IX_SHAREDWITH]
        # check for meeting mime types
        values_to_documents = mimeType_index.values_to_documents
        documents_to_values = mimeType_index.documents_to_values
        doc_ids = values_to_documents.get(OLD_MIMETYPE)
        if doc_ids is not None:
            # change mimetype
            values_to_documents[NEW_MIMETYPE] = doc_ids
            del values_to_documents[OLD_MIMETYPE]
            # reset docs ids
            for doc_id in doc_ids:
                if doc_id in documents_to_values:
                    count += 0
                    documents_to_values[doc_id] = NEW_MIMETYPE
                    # index meeting
                    meeting = intids.queryObject(doc_id)
                    if meeting is not None:
                        sharedWith_index.index_doc(doc_id, meeting)

    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('Evolution %s done. %s object(s) indexed', generation, count)


def evolve(context):
    """
    Evolve to generation 100 by changing the mimeType for meeting objects
    """
    do_evolve(context, generation)
