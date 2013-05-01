#!/usr/bin/env python
"""
Implementation of the link data type.

$Id$
"""
from __future__ import print_function, unicode_literals

from . import interfaces
from nti.externalization import interfaces as ext_interfaces

from zope import interface
from zope import component

import six

import functools

@interface.implementer( interfaces.ILink )
@functools.total_ordering
class Link(object):
	"""
	Default implementation of ILink.
	These are non-persistent and should be generated at runtime.
	"""
	mime_type = 'application/vnd.nextthought.link'
	elements = ()
	target_mime_type = None
	method = None
	title = None

	def __init__( self, target, rel='alternate', elements=(), target_mime_type=None, method=None, title=None ):
		"""
		:param target: The destination object for this link. Required to be
			non-``None``. The exact value of what is accepted depends on
			the externalization process (see :mod:`nti.dataserver.links_external`),
			but is typically a persistent object, a URL, or an NTIID.
		:keyword elements: Additional path components that should be added
			after the target when a URL is generated
		:keyword target_mime_type: If known and given, the mime type that
			can be expected to be found after following the link.
		:keyword str method: If given, the particular HTTP method that is supported
			at this URL.
		:keyword str title: If given, a human-readable description for the link
			(usually localized).
		"""
		__traceback_info__ = target, rel, elements, target_mime_type
		# If the target is None, it won't externalize correctly,
		# which is a very hard error to diagnose the cause of--it was far away.
		# Since it makes no sense to have a None target, we prohibit it
		assert target is not None
		self.rel = rel
		self.target = target

		if elements:
			self.elements = elements
		if target_mime_type:
			self.target_mime_type = target_mime_type
		if method:
			self.method = method
		if title:
			self.title = title

	# Make them non-picklable
	def __reduce__( self, *args, **kwargs ):
		raise TypeError( "Links cannot be pickled." )
	__reduce_ex__ = __reduce__

	def __repr__( self ):
		# Its very easy to get into an infinite recursion here
		# if the target wants to print its links
		return "<Link rel='%s' %s/%s>" % (self.rel, type(self.target), id(self.target))

	def __hash__( self ):
		# In infinite recursion cases we do a terrible job. We only
		# really work in simple cases
		if isinstance(self.target, six.string_types):
			return hash( self.rel + self.target )
		return hash( self.rel )

	def __eq__( self, other ):
		try:
			return self is other or (self.rel == other.rel and self.target == other.target and self.elements == other.elements)
		except AttributeError:
			return NotImplemented

	def __lt__( self, other ):
		try:
			return (self.rel, self.target, self.elements) < (other.rel, other.target, other.elements)
		except AttributeError:
			return NotImplemented

	def __gt__( self, other ):
		try:
			return (self.rel, self.target, self.elements) > (other.rel, other.target, other.elements)
		except AttributeError:
			return NotImplemented

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
