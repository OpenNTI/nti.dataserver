#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Mimetype related interfaces.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

# TODO: Where exactly should this live? there's zope.app.content.interfaces.IContentType, which
# might be what we want? Except it's an IInterface

class IContentTypeMarker(interface.Interface):
	"""
	Marker interface for deriving mimetypes from class names.
	"""
