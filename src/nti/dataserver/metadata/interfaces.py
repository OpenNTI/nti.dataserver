#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.dataserver.interfaces import IIntIdIterable


class IPrincipalMetadataObjects(IIntIdIterable):
    """
    A predicate to return objects can be indexed in the metadata catalog
    for a principal

    These will typically be registered as subscription adapters
    """

    def iter_objects():
        pass
