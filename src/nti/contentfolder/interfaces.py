#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.container.constraints import contains
from zope.container.constraints import containers

from zope.container.interfaces import IContained
from zope.container.interfaces import IContentContainer

from zope.dublincore.interfaces import IDCDescriptiveProperties

from zope.mimetype.interfaces import IContentTypeAware

from plone.namedfile.interfaces import INamed as IPloneNamed

from nti.coremetadata.interfaces import ILastModified

from nti.schema.field import Bool
from nti.schema.field import ValidTextLine

class INamedContainer(IContained,
					  IDCDescriptiveProperties,
					  IContentContainer,
					  IContentTypeAware,
					  ILastModified):
	name = ValidTextLine(title="Folder name", required=True)

	# dublin core
	title = ValidTextLine(title="Folder title", required=False, default=None)
	description = ValidTextLine(title="Folder description", required=False, default=None)

	use_blobs = Bool(title="Use blobs flag", required=True, default=True)
	use_blobs.setTaggedValue('_ext_excluded_out', True)

class IContentFolder(INamedContainer):

	containers(str('.INamedContainer'))
	contains(str('.INamedContainer'),
			 IPloneNamed)

	__parent__.required = False
	__setitem__.__doc__ = None

	def add(obj):
		"""
		add an object to this container
		"""

	def remove(obj):
		"""
		remove the specified object from this container
		"""

	def rename(old, new):
		"""
		rename an stored item
		"""

class IRootFolder(IContentFolder):
	pass
