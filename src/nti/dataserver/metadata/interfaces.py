#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.dataserver.interfaces import IIntIdIterable


class IPrincipalMetadataObjects(IIntIdIterable):
    """
    A predicate to return objects can be indexed in the metadata catalog
    for a principal

    These will typically be registered as subscription adapters
    """

    def iter_objects():
        pass
