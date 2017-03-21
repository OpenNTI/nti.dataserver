#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.dataserver.interfaces import ILink
from nti.dataserver.interfaces import IDataserver

from nti.traversal.traversal import find_nearest_site as nti_find_nearest_site


def find_nearest_site(context):
    """
    Find the nearest :class:`loc_interfaces.ISite` in the lineage of `context`.
    :param context: The object whose lineage to search. If this object happens to be an
            :class:`ILink`, then this attempts to take into account
            the target as well.
    :return: The nearest site. Possibly the root site.
    """

    root = component.getUtility(IDataserver).root
    result = nti_find_nearest_site(context, root, ignore=ILink)
    return result

import zope.deferredimport
zope.deferredimport.initialize()

zope.deferredimport.deprecatedFrom(
    "Moved to nti.traversal.traversal",
    "nti.traversal.traversal",
    "resource_path",
    "normal_resource_path",
    "is_valid_resource_path",
    "find_interface",
    "adapter_request",
    "ContainerAdapterTraversable",
    "DefaultAdapterTraversable"
)
