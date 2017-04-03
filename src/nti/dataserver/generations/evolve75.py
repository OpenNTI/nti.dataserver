#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 75

from functools import partial

from zope import component

from zope.intid.interfaces import IIntIds

from zope.component.hooks import site
from zope.component.hooks import setHooks

from nti.assessment.interfaces import IQInquiry
from nti.assessment.interfaces import IQAssessment

from nti.contenttypes.presentation.interfaces import IPresentationAsset

from nti.metadata import metadata_queue

from nti.site.hostpolicy import run_job_in_all_host_sites


def _index_assets(queue, intids):

    def _index_item(item):
        doc_id = intids.queryId(item)
        if doc_id is not None:
            try:
                queue.add(doc_id)
                return True
            except TypeError:
                pass
        return False

    for _, item in component.getUtilitiesFor(IPresentationAsset):
        _index_item(item)

    for _, item in component.getUtilitiesFor(IQAssessment):
        _index_item(item)

    for _, item in component.getUtilitiesFor(IQInquiry):
        _index_item(item)


def do_evolve(context, generation=generation):
    setHooks()
    conn = context.connection
    root = conn.root()
    dataserver_folder = root['nti.dataserver']

    with site(dataserver_folder):
        assert component.getSiteManager() == dataserver_folder.getSiteManager(), \
               "Hooks not installed?"

        lsm = dataserver_folder.getSiteManager()
        intids = lsm.getUtility(IIntIds)
        queue = metadata_queue()
        if queue is None:
            return

        run_job_in_all_host_sites(partial(_index_assets, queue, intids))

        logger.info('Dataserver evolution %s done.', generation)


def evolve(context):
    """
    Evolve to 75 by indexing assessments, inquiries and assets
    """
    do_evolve(context, generation)
