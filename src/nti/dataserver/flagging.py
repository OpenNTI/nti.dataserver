#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for flagging modeled content.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface
from zope import intid
from zope.intid import interfaces as intid_interfaces
from zope.cachedescriptors.property import CachedProperty

import BTrees
import persistent

from nti.utils import sets
from nti.dataserver import interfaces as nti_interfaces

def flag_object( context, username ):
	"""
	Cause `username` to flag the object `context` for moderation action.

	.. note:: Currently, it does not take the username into account.
	"""

	component.getAdapter( context, nti_interfaces.IGlobalFlagStorage ).flag( context )


def flags_object( context, username ):
	"""
	Returns whether the `context` object has been flagged. This may or may not
	take into account the username who is asking.

	.. note:: Currently, it does not take the username into account.
	"""

	return component.getAdapter( context, nti_interfaces.IGlobalFlagStorage ).is_flagged( context )

def unflag_object( context, username ):
	"""
	Removes the flag status of the username.

	.. note:: Currently, it does not take the username into account.
	"""

	component.getAdapter( context, nti_interfaces.IGlobalFlagStorage ).unflag( context )

@component.adapter(nti_interfaces.IFlaggable,  intid_interfaces.IIntIdRemovedEvent )
def _delete_flagged_object( flaggable, event ):
	unflag_object( flaggable, None )


@interface.implementer(nti_interfaces.IGlobalFlagStorage)
@component.adapter(nti_interfaces.IFlaggable)
def FlaggableGlobalFlagStorageFactory( context ):
	"""
	Finds the global flag storage as a registered utility
	"""

	return component.getUtility( nti_interfaces.IGlobalFlagStorage )

@interface.implementer(nti_interfaces.IGlobalFlagStorage)
class IntIdGlobalFlagStorage(persistent.Persistent):
	"""
	The storage for flags based on simple intids.
	"""

	family = BTrees.family64

	def __init__( self, family=None ):
		if family is None:
			try:
				family = getattr( self._intids, 'family', BTrees.family64 )
			except LookupError:
				family = self.family
		self.flagged = family.II.TreeSet()

	def flag( self, context ):
		self.flagged.add( self._intids.getId( context ) )

	def is_flagged( self, context ):
		try:
			return self._intids.getId( context ) in self.flagged
		except KeyError:
			return False

	def unflag( self, context ):
		sets.discard( self.flagged, self._intids.queryId( context ))

	def iterflagged( self ):
		intids = self._intids
		for iid in self.flagged:
			yield intids.getObject( iid ) # If this fails we are out of sync

	@CachedProperty
	def _intids(self):
		return component.getUtility( intid.IIntIds )
