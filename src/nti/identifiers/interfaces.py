#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

class IExternalIdentifierUtility(interface.Interface):
    """
    A subscriber utility to fetch external identifiers given a user.
    """

    def get_namespaced_external_id(user):
        """
        Fetches the external identifer for the given user. This must be
        appropriately namespaced so that there are not identifer collissions
        across providers/clients.
        """

