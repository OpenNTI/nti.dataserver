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

from zope.location.interfaces import IContained

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.namedfile.file import NamedBlobFile
from nti.namedfile.datastructures import NamedFileObjectIO

from ..interfaces import IContentFile

@interface.implementer(IContentFile, IContained)
class ContentFile(PersistentCreatedModDateTrackingObject,  # Order matters
				  NamedBlobFile):

	__parent__ = __name__ = None

@component.adapter(IContentFile)
class _ContentFileObjectIO(NamedFileObjectIO):

	_ext_iface_upper_bound = IContentFile
	_excluded_in_ivars_ = {'download_url'}.union(NamedFileObjectIO._excluded_in_ivars_)

	def _ext_mimeType(self, obj):
		return u'application/vnd.nextthought.contentfile'

	def toExternalObject(self, mergeFrom=None, **kwargs):
		ext_dict = super(_ContentFileObjectIO, self).toExternalObject(**kwargs)
		return ext_dict

def _ContentFileFactory(ext_obj):
	factory = ContentFile
	return factory
