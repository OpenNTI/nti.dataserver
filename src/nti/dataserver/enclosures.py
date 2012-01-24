#!/usr/bin/env python2.7
"""
Relating to enclosures.
"""

import persistent
import persistent.list # Req'd, despite pylint

from zope.mimetype.interfaces import IContentTypeAware
from zope import interface
from zope.container.interfaces import INameChooser
from zope.container.btree import BTreeContainer

from nti.dataserver import interfaces
from nti.dataserver import datastructures


class SimplePersistentEnclosure(datastructures.CreatedModDateTrackingObject, persistent.Persistent):
	"""
	A trivial implementation of a persistent enclosure.
	Real production usage needs much more thought and should
	use Blobs. Consider the :module:`z3c.blobfile` package. See also zope.dublincore.
	"""

	interface.implements( interfaces.IEnclosedContent,
						  IContentTypeAware,
						  interfaces.IZContained )

	def __init__( self, name, data='', mime_type='text/plain' ):
		super(SimplePersistentEnclosure,self).__init__()
		self.name = name
		self.mime_type = mime_type
		self.data = data
		self.__parent__ = None

	def _get__name__( self ):
		return self.name
	def _set__name__( self, name ):
		self.name = name
	__name__ = property( _get__name__, _set__name__ )


class SimpleEnclosureMixin(object):
	"""
	Provides a basic level of support for enclosures to any object.

	Operates by using an instance variable, `_enclosures` to store a
	zope.container.IContainer of names to enclosures.
	"""

	def __init__(self, *args, **kwargs):
		super(SimpleEnclosureMixin,self).__init__( *args, **kwargs )

	### Enclosures
	# The backing store, the _enclosures BTreeContainer, is created
	# on demand
	def iterenclosures( self ):
		enc = getattr( self, '_enclosures', {} ) or {} # In case of None
		return iter( enc.values() )

	def add_enclosure( self, content ):
		"""
		Adds a new enclosure to this object.

		:param content: An instance of :class:`nti_interfaces.IContent` (esp. :class:`nti_interfaces.IEnclosedContent`)
			This method may change the `name` attribute of this object if
			there is already an enclosure with this name, and the enclosure
			container provides an :class:`INameChooser` adapter.
		:raises KeyError: If the enclosures container enforces uniqueness,
			doesn't allow overwriting, and no unique name can be found.

		EOD
		"""
		if content:
			if getattr( self, '_enclosures', None ) is None:
				setattr( self, '_enclosures', BTreeContainer() )
			enclosures = getattr( self, '_enclosures' )
			name_chooser = INameChooser(enclosures, None)
			if name_chooser:
				content.name = name_chooser.chooseName( content.name, content )
			enclosures[content.name] = content
			# FIXME: Weird stuff to make our weird traversal work
			# out. We're lying about parentage.
			try:
				delattr( content, '__parent__' )
			except AttributeError:
				pass
