#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.contentprocessing.metadata_extractors import ImageMetadata

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalMappingDecorator

from nti.links.links import Link

LINKS = StandardExternalFields.LINKS


@component.adapter(ImageMetadata)
@interface.implementer(IExternalMappingDecorator)
class _ImageMetadataSafeProxyDecorator(AbstractAuthenticatedRequestAwareDecorator):
    """
    Add a link to our safeimage proxy that clients
    can use to proxy the image through us
    """

    def _do_decorate_external(self, context, external):
        links = external.setdefault(LINKS, [])
        root = self.request.route_path('objects.generic.traversal',
                                       traverse=())
        safeimage_link = Link(root,
                              elements=('safeimage',),
                              rel='safeimage',
                              params={'url': context.url})
        links.append(safeimage_link)
