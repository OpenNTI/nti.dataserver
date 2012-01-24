#!/usr/bin/env python2.7
"""
Implementation of the link data type.
"""

from . import interfaces

from zope import interface
from zope import component

class Link(object):
	"""
	Default implementation of ILink.
	These are non-persistent and should be generated at runtime.
	"""

	interface.implements( interfaces.ILink )

	def __init__( self, target, rel='alternate' ):
		self.rel = rel
		self.target = target

	# Make them non-picklable
	def __reduce__( self, *args, **kwargs ):
		raise TypeError( "Links cannot be pickled." )
	__reduce_ex__ = __reduce__

class NoOpLinkExternalObjectAdapter(object):
	"""
	Implementation of :class:`interfaces.IExternalObject` for
	the concrete :class:`Link`. It's intended use is for
	contexts that do not yet understand links (e.g, deprecated code).
	That is why it is so specific.
	"""

	interface.implements(interfaces.IExternalObject)
	component.adapts(Link)

	def __init__( self, link ):
		pass

	def toExternalObject(self):
		return None
