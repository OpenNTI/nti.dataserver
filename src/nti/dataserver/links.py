#!/usr/bin/env python2.7
"""
Implementation of the link data type.
"""

from . import interfaces
from nti.externalization import interfaces as ext_interfaces

from zope import interface
from zope import component

import six

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

	def __repr__( self ):
		# It's very easy to get into an infinite recursion here
		# if the target wants to print its links
		return "<Link rel='%s' %s/%s>" % (self.rel, type(self.target), id(self.target))

	def __hash__( self ):
		# In infinite recursion cases we do a terrible job. We only
		# really work in simple cases
		if isinstance(self.target, six.string_types):
			return hash( self.rel + self.target )
		return hash( self.rel )

	def __eq__( self, other ):
		return other == (self.rel,self.target)

@interface.implementer(ext_interfaces.IExternalObject)
@component.adapter(Link)
class NoOpLinkExternalObjectAdapter(object):
	"""
	Implementation of :class:`interfaces.IExternalObject` for
	the concrete :class:`Link`. It's intended use is for
	contexts that do not yet understand links (e.g, deprecated code).
	That is why it is so specific.
	"""

	def __init__( self, link ):
		pass

	def toExternalObject(self):
		return None
