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

	_enclosures = None

	def __init__(self, *args, **kwargs):
		super(SimpleEnclosureMixin,self).__init__( *args, **kwargs )

	### Enclosures
	# The backing store, the _enclosures BTreeContainer, is created
	# on demand

	def _new_enclosure_container(self):
		return BTreeContainer()

	def iterenclosures( self ):
		enc = self._enclosures or {} # In case of None
		return iter( enc.values() )

	def __setstate__(self,state):
		super(SimpleEnclosureMixin,self).__setstate__(state)
		if self._enclosures is not None and self._enclosures.__parent__ is None:
			self._enclosures.__parent__ = self

	def add_enclosure( self, content ):
		"""
		Adds a new enclosure to this object.

		:param content: An instance of :class:`nti_interfaces.IContent` (esp. :class:`nti_interfaces.IEnclosedContent`)
			This method may change the `name` attribute of this object if
			there is already an enclosure with this name, and the enclosure
			container provides an :class:`INameChooser` adapter.
		:raises KeyError: If the enclosures container enforces uniqueness,
			doesn't allow overwriting, and no unique name can be found.
		:raises AttributeError: If the content has no `name` attribute.

		:returns: The content object

		EOD
		"""
		if content is None:
			return None

		if self._enclosures is None:
			self._enclosures = self._new_enclosure_container()
			self._enclosures.__parent__ = self
			# But notice that the __name__ is left empty...

		enclosures = self._enclosures
		name_chooser = INameChooser(enclosures, None)
		if name_chooser:
			content.name = name_chooser.chooseName( content.name, content )
		enclosures[content.name] = content
		return content


	def get_enclosure( self, name ):
		"""
		Return the enclosure with the given name.
		:raises KeyError: If no such enclosure is found.
		"""

		return (self._enclosures or {})[name]
