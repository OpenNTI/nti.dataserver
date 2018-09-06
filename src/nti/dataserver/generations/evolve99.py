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
from zope import lifecycleevent

from zope.annotation.interfaces import IAnnotations

from zope.component.hooks import site as current_site

from zope.intid.interfaces import IIntIds

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

generation = 99

logger = __import__('logging').getLogger(__name__)


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


def install_catalog(ds_folder, intids):
    try:
        from nti.app.users.index import install_context_lastseen_catalog
        return install_context_lastseen_catalog(ds_folder, intids)
    except ImportError:
        return None


def evolve_user(user):
    count = 0
    try:
        from nti.app.users.adapters import CONTEXT_LASTSEEN_ANNOTATION_KEY
        from nti.app.users.adapters import context_lastseen_factory

        # get old container
        annotations = IAnnotations(user)
        old_container = annotations[CONTEXT_LASTSEEN_ANNOTATION_KEY]
        del annotations[CONTEXT_LASTSEEN_ANNOTATION_KEY]

        # copy
        container = context_lastseen_factory(user)
        for k, v in old_container.items():
            record = container.append(k, v)
            if record is not None:
                count += 1
                lifecycleevent.modified(record)

        # ground
        old_container.__parent__ = None
    except (ImportError, KeyError):
        pass
    return count


def evolve_users(ds_folder):
    count = 0
    users = ds_folder['users']
    for entity in users.values():
        if IUser.providedBy(entity):
            count += evolve_user(entity)
    return count


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

        catalog = install_catalog(ds_folder, intids)
        if catalog is not None:
            count = evolve_users(ds_folder)

    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('Evolution %s done. %s object(s) indexed', generation, count)


def evolve(context):
    """
    Evolve to generation 99 by adding the "context last seen" catalog
    """
    do_evolve(context, generation)
