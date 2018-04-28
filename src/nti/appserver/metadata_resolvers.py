#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implements :mod:`nti.contentprocessing.metadata_extractors` related
functionality

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from nti.contentprocessing.interfaces import IContentMetadata
from nti.contentprocessing.interfaces import IContentMetadataURLHandler

from nti.ntiids.ntiids import find_object_with_ntiid

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IContentMetadataURLHandler)
class TagURLHandler(object):
    """
    Registered as a URL handler for the NTIID URL scheme,
    ``tag:``. If something is found, adapts it to :class:`IContentMetadata`.
    """

    def __call__(self, url):
        obj = find_object_with_ntiid(url)
        if obj is not None:
            return IContentMetadata(obj, None)
