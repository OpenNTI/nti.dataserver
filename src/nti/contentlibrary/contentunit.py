#!/usr/bin/env python
"""
Generic implementations of IContentUnit functions
"""
from __future__ import print_function, unicode_literals
logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.utils.property import alias
from nti.contentlibrary.interfaces import IContentUnit, IContentPackage


@interface.implementer(IContentUnit)
class ContentUnit(object):
	"""
	Simple implementation of :class:`IContentUnit`.
	"""

	__external_class_name__ = 'ContentUnit'

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
			__traceback_info__ = k, v
			if hasattr( self, k ):
				setattr( self, k, v )
			else: # pragma: no cover
				logger.warn( "Ignoring unknown key %s = %s", k, v )

	__name__ = alias( 'title' )
	label = alias( 'title' )


	def __repr__( self ):
		return "<%s.%s '%s' '%s'>" % (self.__class__.__module__, self.__class__.__name__,
									  self.__name__, getattr( self, 'key', self.href) )


@interface.implementer(IContentPackage)
class ContentPackage(ContentUnit):
	"""
	Simple implementation of :class:`IContentPackage`.
	"""

	__external_class_name__ = 'ContentPackage'

	root = None
	index = None
	index_last_modified = None
	index_jsonp = None
	installable = False
	archive = None
	archive_unit = None
	renderVersion = 1

	# IDCExtended
	creators = ()
	subjects = ()
	contributors = ()
	publisher = ''
