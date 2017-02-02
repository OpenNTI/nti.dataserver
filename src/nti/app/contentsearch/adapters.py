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

from nti.contenttypes.presentation.interfaces import INTITranscript

from nti.contentsearch.interfaces import IResultTransformer


@component.adapter(INTITranscript)
@interface.implementer(IResultTransformer)
def transcript_to_media(obj):
    return obj.__parent__
