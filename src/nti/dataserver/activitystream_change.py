#!/usr/bin/env python
"""
Functions and architecture for general activity streams.
"""

from __future__ import print_function, unicode_literals, absolute_import

import weakref
import persistent

from zope import interface
from zope import component

from nti.dataserver import datastructures
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import mimetype

from nti.externalization.datastructures import LocatedExternalDict
from nti.externalization.oids import toExternalOID
from nti.externalization.externalization import toExternalObject
from nti.externalization import interfaces as ext_interfaces
from nti.externalization.interfaces import StandardExternalFields

@interface.implementer(nti_interfaces.IStreamChangeEvent,nti_interfaces.IZContained)
class Change(persistent.Persistent,datastructures.CreatedModDateTrackingObject):
	"""
	A change notification. For convenience, it acts like a
	Contained object if the underlying object was Contained.
	It externalizes to include the ChangeType, Creator, and Item.
	"""

	CREATED  = nti_interfaces.SC_CREATED
	MODIFIED = nti_interfaces.SC_MODIFIED
	DELETED  = nti_interfaces.SC_DELETED
	SHARED   = nti_interfaces.SC_SHARED
	CIRCLED  = nti_interfaces.SC_CIRCLED

	useSummaryExternalObject = False

	__name__ = None
	__parent__ = None

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

		for k in ('id', 'containerId', '__name__', '__parent__'):
			v = getattr( obj, k, None )
			if v is not None:
				setattr( self, k, v )

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

	def values(self):
		"""
		For migration compatibility with :mod:`zope.generations.utility`, this
		method returns the same thing as :meth:`object`.
		"""
		yield self.object

	def __repr__(self):
		return "%s('%s',%s)" % (self.__class__.__name__,self.type,type(self.object).__name__)


@interface.implementer(ext_interfaces.IExternalObject)
@component.adapter(nti_interfaces.IStreamChangeEvent)
class _ChangeExternalObject(object):

	def __init__( self, change ):
		self.change = change

	def toExternalObject(self):
		change = self.change
		wrapping = change.object

		result = LocatedExternalDict()
		result.__parent__ = getattr( wrapping, '__parent__', getattr( change, '__parent__', None ) )
		result.__name__ = getattr( wrapping, '__name__', getattr( change, '__name__', None ) )
		result[StandardExternalFields.CLASS] = 'Change'
		result[StandardExternalFields.MIMETYPE] = mimetype.nti_mimetype_with_class( 'Change' )


		result[StandardExternalFields.LAST_MODIFIED] = change.lastModified
		result[StandardExternalFields.CREATOR] = None
		if change.creator:
			result[StandardExternalFields.CREATOR] = change.creator.username if hasattr( change.creator, 'username' ) else change.creator

		result['ChangeType'] = change.type
		result[StandardExternalFields.ID] = change.id or None
		# OIDs must be unique
		result[StandardExternalFields.OID] = toExternalOID( change )
		#if result['OID'] is None:
		#	del result['OID']
		result['Item'] = None
		if wrapping is not None:
			result['Item'] = toExternalObject( change.object, name=('summary' if change.useSummaryExternalObject else '') )
		return result
