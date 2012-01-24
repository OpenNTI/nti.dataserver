#!/usr/bin/env python2.7

"""
Functions and architecture for general activity streams.
"""

import weakref

import persistent
import datastructures

class Change(persistent.Persistent,datastructures.CreatedModDateTrackingObject,datastructures.ContainedMixin):
	"""
	A change notification. For convenience, it acts like a
	Contained object if the underlying object was Contained.
	It externalizes to include the ChangeType, Creator, and Item.
	"""
	CREATED  = "Created"
	MODIFIED = "Modified"
	DELETED  = "Deleted"
	SHARED   = "Shared"
	CIRCLED  = "Circled"

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
		self.id = getattr( obj, 'id', None )
		self.containerId = getattr( obj, 'containerId', None )
		# We don't copy the object's modification date,
		# we have our own
		self.updateLastMod()
		self.useSummaryExternalObject = False

	@property
	def object(self):
		""" Returns the object to which this reference refers,
		or None if the object no longer exists. """
		return self.objectReference()

	def __repr__(self):
		return "%s('%s',%s)" % (self.__class__.__name__,self.type,self.object)

	def __str__(self):
		return str(self.toExternalObject())

	def toExternalObject(self):
		result = {}
		result['Last Modified'] = self.lastModified
		if self.creator:
			result['Creator'] = self.creator.username if hasattr( self.creator, 'username' ) else self.creator
		result['Class'] = 'Change'
		result['ChangeType'] = self.type
		if self.id:
			result['ID'] = self.id
		# OIDs must be unique
		result['OID'] = datastructures.toExternalOID( self )
		if result['OID'] is None:
			del result['OID']
		if self.object is not None:
			result['Item'] = datastructures.toExternalObject( self.object ) \
							 if not getattr( self, 'useSummaryExternalObject', False ) \
							 else self.object.toSummaryExternalObject()
		return result
