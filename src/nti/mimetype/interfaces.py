#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Mimetype related interfaces.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

class IContentTypeMarker(interface.Interface):
	"""
	Marker interface for deriving mimetypes from class names.
	"""
