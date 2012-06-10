#!/usr/bin/env python
"""
Datastructures to help externalization.
$Revision$
"""
from __future__ import unicode_literals, print_function

import logging
logger = logging.getLogger( __name__ )

import ZODB

from zope import interface
from zope import component
from zope.location import ILocation

from .interfaces import IExternalObject, IInternalObjectIO, ILocatedExternalMapping, ILocatedExternalSequence, StandardInternalFields, StandardExternalFields
from .externalization import toExternalDictionary, toExternalObject

def _syntheticKeys( ):
	return ('OID', 'ID', 'Last Modified', 'Creator', 'ContainerId', 'Class')

def _isMagicKey( key ):
	""" For our mixin objects that have special keys, defines
	those keys that are special and not settable by the user. """
	return key in _syntheticKeys()

isSyntheticKey = _isMagicKey


class LocatedExternalDict(dict):
	"""
	A dictionary that implements ILocation. Returned
	by toExternalDictionary.
	"""
	interface.implements( ILocatedExternalMapping )
	__name__ = ''
	__parent__ = None
	__acl__ = ()

class LocatedExternalList(list):
	"""
	A list that implements ILocation. Returned
	by toExternalObject.
	"""
	interface.implements( ILocatedExternalSequence )
	__name__ = ''
	__parent__ = None
	__acl__ = ()

class ExternalizableDictionaryMixin(object):
	""" Implements a toExternalDictionary method as a base for subclasses. """

	def __init__(self, *args):
		super(ExternalizableDictionaryMixin,self).__init__(*args)

	def _ext_replacement( self ):
		return self

	def toExternalDictionary( self, mergeFrom=None):
		return toExternalDictionary( self._ext_replacement(), mergeFrom=mergeFrom )

	def stripSyntheticKeysFromExternalDictionary( self, external ):
		""" Given a mutable dictionary, removes all the external keys
		that might have been added by toExternalDictionary and echoed back. """
		for k in _syntheticKeys():
			external.pop( k, None )
		return external

@interface.implementer(IInternalObjectIO)
class ExternalizableInstanceDict(ExternalizableDictionaryMixin):
	"""Externalizes to a dictionary containing the members of __dict__ that do not start with an underscore."""

	# TODO: there should be some better way to customize this if desired (an explicit list)
	# TODO: Play well with __slots__
	# TODO: This won't evolve well. Need something more sophisticated,
	# probably a meta class.

	# Avoid things super handles
	_excluded_out_ivars_ = {StandardInternalFields.ID, StandardExternalFields.ID, StandardInternalFields.CREATOR,
							StandardExternalFields.CREATOR, StandardInternalFields.CONTAINER_ID,
							'lastModified', StandardInternalFields.LAST_MODIFIEDU, StandardInternalFields.CREATED_TIME,
							'links'}
	_excluded_in_ivars_ = {StandardInternalFields.ID, StandardExternalFields.ID,
						   StandardExternalFields.OID,
						   StandardInternalFields.CREATOR,
						   StandardExternalFields.CREATOR,
						   'lastModified',
						   StandardInternalFields.LAST_MODIFIEDU,
						   StandardExternalFields.CLASS,
						   StandardInternalFields.CONTAINER_ID}
	_prefer_oid_ = False
	_update_accepts_type_attrs = False

	def toExternalDictionary( self, mergeFrom=None ):
		result = super(ExternalizableInstanceDict,self).toExternalDictionary( mergeFrom=mergeFrom )
		ext_self = self._ext_replacement()
		for k in ext_self.__dict__:
			if (k not in self._excluded_out_ivars_  # specifically excluded
				and not k.startswith( '_' )			# private
				and not k in result					# specifically given
				and not callable(getattr(ext_self,k))):	# avoid functions

				result[k] = toExternalObject( getattr( ext_self, k ) )
				if ILocation.providedBy( result[k] ):
					result[k].__parent__ = self
		if StandardExternalFields.ID in result and StandardExternalFields.OID in result \
			   and self._prefer_oid_ and result[StandardExternalFields.ID] != result[StandardExternalFields.OID]:
			result[StandardExternalFields.ID] = result[StandardExternalFields.OID]
		return result

	def toExternalObject( self, mergeFrom=None ):
		return self.toExternalDictionary(mergeFrom)

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		ext_self = self._ext_replacement()
		for k in parsed:
			if k in self._excluded_in_ivars_:
				continue
			if (self._update_accepts_type_attrs and hasattr( ext_self, k ) ) or k in ext_self.__dict__:
				setattr( ext_self, k, parsed[k] )

		if StandardExternalFields.CONTAINER_ID in parsed and getattr( ext_self, StandardInternalFields.CONTAINER_ID, parsed ) is None:
			setattr( ext_self, StandardInternalFields.CONTAINER_ID, parsed[StandardExternalFields.CONTAINER_ID] )
		if StandardExternalFields.CREATOR in parsed and getattr( ext_self, StandardExternalFields.CREATOR, parsed ) is None:
			setattr( ext_self, StandardExternalFields.CREATOR, parsed[StandardExternalFields.CREATOR] )

	def __repr__( self ):
		try:
			return "%s().__dict__.update( %s )" % (self.__class__.__name__, self.toExternalDictionary() )
		except ZODB.POSException.ConnectionStateError:
			return '%s(Ghost)' % self.__class__.__name__
		except (ValueError,LookupError) as e: # Things like invalid NTIID, missing registrations
			return '%s(%s)' % (self.__class__.__name__, e)
