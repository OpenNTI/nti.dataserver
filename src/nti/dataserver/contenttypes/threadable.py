#!/usr/bin/env python
"""
Defines the base behaviours for things that are threadable.
"""
from __future__ import print_function, unicode_literals

import collections

from persistent.list import PersistentList
from nti.externalization.oids import to_external_ntiid_oid
from nti.dataserver import interfaces as nti_interfaces

class ThreadableMixin(object):
	"""
	Defines an object that is client-side threadable. These objects are
	threaded like email (RFC822?). We assume a single parent and
	maintain a list of ancestors in order up to the root (or the last
	thing that was threadable.
	"""

	__external_oids__ = ['inReplyTo', 'references']

	# Our one single parent
	_inReplyTo = None
	# Our chain of references back to the root
	_references = ()

	def __init__(self):
		super(ThreadableMixin,self).__init__()

	def getInReplyTo(self):
		return self._inReplyTo() if self._inReplyTo else None

	def setInReplyTo( self, value ):
		self._inReplyTo = nti_interfaces.IWeakRef( value ) if value is not None else None

	inReplyTo = property( getInReplyTo, setInReplyTo )

	@property
	def references(self):
		return [x() for x in self._references if x() is not None]

	def addReference( self, value ):
		if value is not None:
			if not self._references:
				self._references = PersistentList()
			self._references.append( nti_interfaces.IWeakRef( value ) )

	def clearReferences( self ):
		if self._references:
			del self._references

class ThreadableExternalizableMixin(ThreadableMixin):
	"""
	Extends :class:`ThreadableMixin` with support for externalizing to and from a dictionary.
	Note that subclasses must extend something that is itself externalizable, and use
	cooperative super-class to be able to put this in the right order.
	"""

	def toExternalObject(self):
		extDict = super(ThreadableExternalizableMixin,self).toExternalObject()
		assert isinstance( extDict, collections.Mapping )
		inReplyTo = self.inReplyTo
		if inReplyTo is not None:
			extDict['inReplyTo'] = to_external_ntiid_oid( inReplyTo )

		extRefs = [] # Order matters
		for ref in self.references:
			extRefs.append( to_external_ntiid_oid( ref ) )
		if extRefs:
			extDict['references'] = extRefs
		return extDict

	def updateFromExternalObject( self, parsed, **kwargs ):
		assert isinstance( parsed, collections.Mapping )
		inReplyTo = parsed.pop( 'inReplyTo', None )
		references = parsed.pop( 'references', [] )
		super(ThreadableExternalizableMixin, self).updateFromExternalObject( parsed, **kwargs )

		self.inReplyTo = inReplyTo
		self.clearReferences()
		for ref in references:
			self.addReference( ref )
