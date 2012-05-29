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

from .interfaces import IExternalObject, ILocatedExternalMapping, ILocatedExternalSequence, StandardInternalFields, StandardExternalFields
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

	def toExternalDictionary( self, mergeFrom=None):
		return toExternalDictionary( self, mergeFrom=mergeFrom )

	def stripSyntheticKeysFromExternalDictionary( self, external ):
		""" Given a mutable dictionary, removes all the external keys
		that might have been added by toExternalDictionary and echoed back. """
		for k in _syntheticKeys():
			external.pop( k, None )
		return external

class ExternalizableInstanceDict(ExternalizableDictionaryMixin):
	"""Externalizes to a dictionary containing the members of __dict__ that do not start with an underscore."""
	interface.implements(IExternalObject)
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

	def toExternalDictionary( self, mergeFrom=None ):
		result = super(ExternalizableInstanceDict,self).toExternalDictionary( mergeFrom=mergeFrom )
		for k in self.__dict__:
			if (k not in self._excluded_out_ivars_  # specifically excluded
				and not k.startswith( '_' )			# private
				and not k in result					# specifically given
				and not callable(getattr(self,k))):	# avoid functions

				result[k] = toExternalObject( getattr( self, k ) )
				if ILocation.providedBy( result[k] ):
					result[k].__parent__ = self
		if StandardExternalFields.ID in result and StandardExternalFields.OID in result \
			   and self._prefer_oid_ and result[StandardExternalFields.ID] != result[StandardExternalFields.OID]:
			result[StandardExternalFields.ID] = result[StandardExternalFields.OID]
		return result

	def toExternalObject( self, mergeFrom=None ):
		return self.toExternalDictionary(mergeFrom)

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		for k in parsed:
			if k in self.__dict__ and k not in self._excluded_in_ivars_:
				setattr( self, k, parsed[k] )

		if StandardExternalFields.CONTAINER_ID in parsed and getattr( self, StandardInternalFields.CONTAINER_ID, parsed ) is None:
			setattr( self, StandardInternalFields.CONTAINER_ID, parsed[StandardExternalFields.CONTAINER_ID] )
		if StandardExternalFields.CREATOR in parsed and getattr( self, StandardExternalFields.CREATOR, parsed ) is None:
			setattr( self, StandardExternalFields.CREATOR, parsed[StandardExternalFields.CREATOR] )

	def __repr__( self ):
		try:
			return "%s().__dict__.update( %s )" % (self.__class__.__name__, self.toExternalDictionary() )
		except ZODB.POSException.ConnectionStateError:
			return '%s(Ghost)' % self.__class__.__name__
		except (ValueError,LookupError) as e: # Things like invalid NTIID, missing registrations
			return '%s(%s)' % (self.__class__.__name__, e)
