#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from pyramid.threadlocal import get_current_request

from nti.app.contentfile.interfaces import IExternalLinkProvider

from nti.app.contentfile.view_mixins import to_external_download_oid_href


@interface.implementer(IExternalLinkProvider)
class DefaultExternalLinkProvider(object):

    def __init__(self, context, request=None):
        self.context = context
        self.request = request or get_current_request()

    def link(self):
        return to_external_download_oid_href(self.context)