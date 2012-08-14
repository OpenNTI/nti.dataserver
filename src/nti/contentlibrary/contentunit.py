#!/usr/bin/env python
"""
Generic implementations of IContentUnit functions
"""
from __future__ import print_function, unicode_literals
logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.contentlibrary.interfaces import IContentUnit, IContentPackage


@interface.implementer(IContentUnit)
class ContentUnit(object):
	"""
	Simple implementation of :class:`IContentUnit`.
	"""

	ordinal = 1
	href = None
	ntiid = None
	icon = None

	# DCDescriptiveProperties
	title = None
	description = None


	children = ()
	__parent__ = None

	def __init__( self, **kwargs ):
		for k, v in kwargs.items():
			if hasattr( self, k ):
				setattr( self, k, v )

	def _get_name(self):
		return self.title
	def _set_name(self,n):
		self.title = n
	__name__ = property(_get_name,_set_name, None, "a synonym for title")
	label = __name__


@interface.implementer(IContentPackage)
class ContentPackage(ContentUnit):
	"""
	Simple implementation of :class:`IContentPackage`.
	"""

	root = None
	index = None
	index_last_modified = None
	installable = False
	archive = None
	renderVersion = 1

	# IDCExtended
	creators = ()
	subjects = ()
	contributors = ()
	publisher = ''
