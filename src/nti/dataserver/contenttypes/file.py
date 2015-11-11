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

from nti.namedfile.file import NamedBlobFile
from nti.namedfile.datastructures import NamedFileObjectIO

from ..interfaces import IContentFile

from .base import UserContentRoot

from .threadable import ThreadableMixin

@interface.implementer(IContentFile, IContained)
class ContentFile(ThreadableMixin,
				  UserContentRoot,
				  NamedBlobFile):

	def __init__(self, *args, **kwargs):
		ThreadableMixin.__init__(self)
		NamedBlobFile.__init__(self, *args, **kwargs)
		self.parameters = {}  # required for schema validation

@component.adapter(IContentFile)
class _ContentFileObjectIO(NamedFileObjectIO):

	_ext_iface_upper_bound = IContentFile
	_excluded_in_ivars_ = {'download_url'}.union(NamedFileObjectIO._excluded_in_ivars_)

	def _ext_mimeType(self, obj):
		return u'application/vnd.nextthought.contentfile'

	def updateFromExternalObject(self, parsed, *args, **kwargs):
		result = super(_ContentFileObjectIO, self).updateFromExternalObject(parsed, *args, **kwargs)
		ext_self = self._ext_replacement()
		assert ext_self.name, 'must provide a content file name'
		return result

def _ContentFileFactory(ext_obj):
	factory = ContentFile
	return factory
