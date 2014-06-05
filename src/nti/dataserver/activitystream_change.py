#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Functions and architecture for general activity streams.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from operator import setitem

from zope import interface
from zope import component
from zope.interface.declarations import ObjectSpecificationDescriptor

from ZODB.POSException import POSError

from nti.mimetype import mimetype
from nti.dataserver import datastructures
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.authorization_acl import ACL

from nti.externalization.oids import toExternalOID
from nti.externalization import interfaces as ext_interfaces
from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.externalization import toExternalObject
from nti.externalization.interfaces import StandardExternalFields

from nti.wref import interfaces as wref_interfaces

def _weak_ref_to( obj ):
	try:
		return wref_interfaces.IWeakRef(obj)
	except TypeError:
		return obj # For the sake of old tests, we allow things that cannot be weakly ref'd.

class _DynamicChangeTypeProvidedBy(ObjectSpecificationDescriptor):
	def __get__(self, inst, cls):
		result = ObjectSpecificationDescriptor.__get__(self, inst, cls)

		if inst is not None and inst.type in nti_interfaces.SC_CHANGE_TYPE_MAP:
			result = result + nti_interfaces.SC_CHANGE_TYPE_MAP[inst.type]
		return result


@interface.implementer(nti_interfaces.IStreamChangeEvent,
					   nti_interfaces.IZContained)
class Change(datastructures.PersistentCreatedModDateTrackingObject):
	"""
	A change notification. For convenience, it acts like a
	Contained object if the underlying object was Contained.
	It externalizes to include the ChangeType, Creator, and Item.

	Because changes are meant to be part of an ongoing stream of
	activity, which may be cached in many different places that are
	not necessarily planned for or easy to find, these objects only
	keep a weak reference to the modified object. For that same
	reason, they only keep a weak reference to their `creator`
	(which must be set after construction).

	If there is a knows sub-interface for the particular kind of
	change type this object represents, it will provide that interface.
	We do this dynamically to avoid issues if certain change types come
	and go across different sites or configurations.
	"""

	mimeType = mimetype.nti_mimetype_with_class( b'Change' )
	mime_type = mimeType
	parameters = {} # immutable

	CREATED  = nti_interfaces.SC_CREATED
	MODIFIED = nti_interfaces.SC_MODIFIED
	DELETED  = nti_interfaces.SC_DELETED
	SHARED   = nti_interfaces.SC_SHARED
	CIRCLED  = nti_interfaces.SC_CIRCLED

	#: If set to `True` (not the default) then when this object
	#: is externalized, the externalizer named "summary" will
	#: be used for the enclosed object.
	useSummaryExternalObject = False

	#: If set to a callable object, then before doing any externalization,
	#: we will call this object with the non-None object we hold,
	#: and externalize the results.
	#: This can be used to do some transformation of the contained object
	#: when it is convenient to hold one thing but externalize another
	#: (e.g., when the external object cannot be persisted.) Note
	#: that if you assign to this property it must be a valid persistent
	#: object, such as a module global.
	externalObjectTransformationHook = None
	# JAM: I'm not quite happy with the above. it's convenient, but is it
	# the best abstraction?

	object_is_shareable = property( lambda self: self.__dict__.get('_v_object_is_shareable', None),
									lambda self, val: setitem( self.__dict__, '_v_object_is_shareable', val ) )
	# FIXME: So badly wrong at this level
	send_change_notice = property(  lambda self: self.__dict__.get('_v_send_change_notice', True), # default to true
									lambda self, val: setitem( self.__dict__, '_v_send_change_notice', val ) )

	__name__ = None
	__parent__ = None

	# Notice we do not inherit from ContainedMixin, and we do not implement
	# IContained. We do that conditionally if the object we're wrapping
	# has these things
	id = None
	containerId = None
	type = None

	__providedBy__ = _DynamicChangeTypeProvidedBy()

	def __init__( self, changeType, obj ):
		super(Change,self).__init__()
		self.type = changeType
		# We keep a weak reference to the object, but
		# we actually store the container information so that it's
		# useful after the object goes away
		self.objectReference = _weak_ref_to( obj )

		for k in ('id', 'containerId', '__name__', '__parent__'):
			v = getattr( obj, k, None )
			if v is not None:
				setattr( self, str(k), v ) # ensure native string in dict

		if self.id and self.containerId:
			interface.alsoProvides( self, nti_interfaces.IContained )
		# We don't copy the object's modification date,
		# we have our own
		self.updateLastMod()

	def _get_creator( self ):
		creator = self.__dict__.get('creator')
		if creator and callable(creator):
			creator = creator() # unwrap weak refs. Older or test objects may not have weak refs
		return creator
	def _set_creator( self, new_creator ):
		if new_creator:
			new_creator = _weak_ref_to( new_creator )
		self.__dict__[str('creator')] = new_creator # ensure native string in dict
	creator = property(_get_creator,_set_creator)

	@property
	def object(self):
		""" Returns the object to which this reference refers,
		or None if the object no longer exists. """
		return self.objectReference()

	#: If true (not the default) we will assume the ACL of our contained
	#: object at access time.
	__copy_object_acl__ = False

	def __acl__(self):
		if not self.__copy_object_acl__:
			return () # No opinion
		o = self.object
		if o is None:
			return () # Gone
		return ACL(o, ())

	def values(self):
		"""
		For migration compatibility with :mod:`zope.generations.utility`, this
		method returns the same thing as :meth:`object`.
		"""
		yield self.object

	def is_object_shareable(self):
		"""
		Returns true if the object is supposed to be copied into local shared data.
		"""
		if self.object_is_shareable is not None:
			return self.object_is_shareable

		result = not nti_interfaces.INeverStoredInSharedStream.providedBy( self.object )
		# We assume this won't change for the lifetime of the object
		self.object_is_shareable = result
		return result

	def __repr__(self):
		try:
			return "%s('%s',%s)" % (self.__class__.__name__, self.type, self.object.__class__.__name__)
		except (POSError,AttributeError):
			return object.__repr__( self )

@interface.implementer(ext_interfaces.IExternalObject)
@component.adapter(nti_interfaces.IStreamChangeEvent)
class _ChangeExternalObject(object):

	def __init__( self, change ):
		self.change = change

	def toExternalObject(self, **kwargs):
		kwargs.pop('name', None)
		change = self.change
		wrapping = change.object
		if wrapping is not None and callable(change.externalObjectTransformationHook):
			wrapping = change.externalObjectTransformationHook(wrapping)

		result = LocatedExternalDict()
		result.__parent__ = getattr( wrapping, '__parent__', getattr( change, '__parent__', None ) )
		result.__name__ = getattr( wrapping, '__name__', getattr( change, '__name__', None ) )
		result[StandardExternalFields.CLASS] = 'Change'
		result[StandardExternalFields.MIMETYPE] = Change.mimeType


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
			result['Item'] = toExternalObject( change.object, name=('summary' if change.useSummaryExternalObject else ''), **kwargs )
		return result
