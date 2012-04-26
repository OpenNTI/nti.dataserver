#!/usr/bin/env python2.7

"""
Functions and architecture for general activity streams.
"""

import weakref
import persistent

from zope import interface
from zope import component

from nti.dataserver import  datastructures
from nti.dataserver import interfaces as nti_interfaces

from nti.externalization.datastructures import LocatedExternalDict
from nti.externalization.oids import toExternalOID
from nti.externalization.externalization import toExternalObject

class Change(persistent.Persistent,datastructures.CreatedModDateTrackingObject):
	"""
	A change notification. For convenience, it acts like a
	Contained object if the underlying object was Contained.
	It externalizes to include the ChangeType, Creator, and Item.
	"""
	interface.implements(nti_interfaces.IStreamChangeEvent)

	CREATED  = nti_interfaces.SC_CREATED
	MODIFIED = nti_interfaces.SC_MODIFIED
	DELETED  = nti_interfaces.SC_DELETED
	SHARED   = nti_interfaces.SC_SHARED
	CIRCLED  = nti_interfaces.SC_CIRCLED

	useSummaryExternalObject = False

	# Notice we do not inherit from ContainedMixin, and we do not implement
	# IContained. We do that conditionally if the object we're wrapping
	# has these things
	id = None
	containerId = None

	def __init__( self, changeType, obj ):
		super(Change,self).__init__()
		self.type = changeType
		# We keep a weak reference to the object, but
		# we actually store the container information so that it's
		# useful after the object goes away
		if hasattr( obj, '_p_oid' ):
			self.objectReference = persistent.wref.WeakRef( obj )
		else:
			self.objectReference = weakref.ref( obj )
		_id = getattr( obj, 'id', None )
		if _id: self.id = _id
		_containerId = getattr( obj, 'containerId', None )
		if _containerId: self.containerId = _containerId

		if self.id and self.containerId:
			interface.alsoProvides( self, nti_interfaces.IContained )
		# We don't copy the object's modification date,
		# we have our own
		self.updateLastMod()

	@property
	def object(self):
		""" Returns the object to which this reference refers,
		or None if the object no longer exists. """
		return self.objectReference()

	def __repr__(self):
		return "%s('%s',%s)" % (self.__class__.__name__,self.type,type(self.object).__name__)


class _ChangeExternalObject(object):
	interface.implements(nti_interfaces.IExternalObject)
	component.adapts(nti_interfaces.IStreamChangeEvent)

	def __init__( self, change ):
		self.change = change

	def toExternalObject(self):
		result = LocatedExternalDict()
		change = self.change
		result['Last Modified'] = change.lastModified
		if change.creator:
			result['Creator'] = change.creator.username if hasattr( change.creator, 'username' ) else change.creator
		result['Class'] = 'Change'
		result['ChangeType'] = change.type
		if change.id:
			result['ID'] = change.id
		# OIDs must be unique
		result['OID'] = toExternalOID( change )
		if result['OID'] is None:
			del result['OID']
		if change.object is not None:
			result['Item'] = toExternalObject( change.object, name=('summary' if change.useSummaryExternalObject else '') )
		return result
