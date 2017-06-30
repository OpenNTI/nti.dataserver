#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface


class IExternalLinkProvider(interface.Interface):
    """
    Adpter for content file exernal providers"
    """

    def link():
        """
        return the external link of a content file
        """
