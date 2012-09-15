#!/usr/bin/env python
"""
Base functionality.
"""
from __future__ import print_function, unicode_literals

import persistent
import collections


from nti.externalization.interfaces import IExternalObject
from nti.externalization.externalization import stripSyntheticKeysFromExternalDictionary, toExternalObject


from nti.dataserver import datastructures
from nti.dataserver import mimetype
from nti.dataserver import sharing
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import users
from nti.ntiids import ntiids

from zope import interface


def _get_entity( username, dataserver=None ):
	return users.Entity.get_entity( username, dataserver=dataserver, _namespace=users.User._ds_namespace )


# TODO: These objects should probably implement IZContained (__name__,__parent__). Otherwise they
# often wind up wrapped in container proxy objects, which is confusing. There may be
# traversal implications to that though, that need to be considered. See also classes.py
@interface.implementer(nti_interfaces.IModeledContent,IExternalObject)
class UserContentRoot(sharing.ShareableMixin, datastructures.ContainedMixin, datastructures.CreatedModDateTrackingObject, persistent.Persistent):
	"""
	Base implementation of behaviours expected for contenttypes. Should be the primary
	superclass for subclasses.

	By default, if an update comes in with only new sharing information,
	and we have been previously saved, then we do not clear our
	other contents. Subclasses can override this by setting canUpdateSharingOnly
	to false.

	Subclasses must arrange for there to be an implementation of toExternalDictionary.

	"""
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass


	canUpdateSharingOnly = True
	__external_can_create__ = True

	def __init__(self):
		super(UserContentRoot,self).__init__()

	def toExternalObject( self ):
		extDict = getattr( self, 'toExternalDictionary' )()

		# Return the values of things we're sharing with. Note that instead of
		# just using the 'username' attribute directly ourself, we are externalizing
		# the whole object and returning the externalized value of the username.
		# This lets us be consistent with any cases where we are playing games
		# with the external value of the username, such as with DynamicFriendsLists
		ext_shared_with = []
		for entity in self.sharingTargets:
			# NOTE: This entire process does way too much work for as often as this
			# is called so we hack this and couple it tightly to when we think
			# we need to use it
			#ext_shared_with.append( toExternalObject( entity )['Username'] )
			username = entity.username if isinstance(entity,users.User) else toExternalObject(entity)['Username']
			ext_shared_with.append( username )

		extDict['sharedWith'] = ext_shared_with
		return extDict

	def _is_update_sharing_only( self, parsed ):
		"""
		Call this after invoking this objects (super's) implementation of
		updateFromExternalObject. If it returns a true value,
		you should take no action.
		"""
		# TODO: I don't like this. It requires all subclasses
		# to be complicit
		parsed = stripSyntheticKeysFromExternalDictionary( dict( parsed ) )
		return len(parsed) == 0 and self.canUpdateSharingOnly and self._p_jar

	def updateFromExternalObject( self, ext_parsed, *args, **kwargs ):
		assert isinstance( ext_parsed, collections.Mapping )
		# Remove some things that may come in (in a copy!)
		parsed = ext_parsed

		# It's important that they stay stripped so that our
		# canUpdateSharingOnly check works (len = 0)

		# Replace sharing with the incoming data.
		sharedWith = parsed.pop( 'sharedWith', () )
		targets = set()
		for s in sharedWith or ():
			target = s
			if _get_entity( s ):
				target = _get_entity( s )
			elif hasattr( self.creator, 'getFriendsList' ):
				# This branch is semi-deprecated. They should send in
				# the NTIID of the list...once we apply security here
				target = self.creator.getFriendsList( s )

			if (target is s or target is None) and ntiids.is_valid_ntiid_string( s ):
				# Any thing else that is a username iterable,
				# in which we are contained (e.g., a class section we are enrolled in)
				# This last clause is our nod to security; need to be firmer

				obj = ntiids.find_object_with_ntiid( s )
				iterable = nti_interfaces.IUsernameIterable( obj, None )
				if iterable is not None:
					ents = set()
					for uname in iterable:
						ent = _get_entity( uname )
						if ent:
							ents.add( ent )
					if self.creator in ents:
						ents.discard( self.creator ) # don't let the creator slip in there
						target = tuple(ents)


			# We only add target, and only if it is non-none and
			# resolver. Otherwise we are falsely implying sharing
			# happened when it really didn't
			if target is not s and target is not None:
				targets.add( target or s )
		self.updateSharingTargets( targets )

		if self._is_update_sharing_only( parsed ):
			# In this state, we have received an update only for sharing.
			# and so do not need to do anything else. We're a saved
			# object already. If we're not saved already, we cannot
			# be created with just this
			pass
		elif len(stripSyntheticKeysFromExternalDictionary( dict( parsed ) )) == 0:
			raise ValueError( "Updating non-saved object: The body must have some data, cannot be empty" )

		s = super(UserContentRoot,self)
		if hasattr( s, 'updateFromExternalObject' ):
			# Notice we pass on the original dictionary
			getattr( s, 'updateFromExternalObject' )(ext_parsed, *args, **kwargs )

def _make_getitem( attr_name ):
	def __getitem__( self, i ):
		attr = getattr( self, attr_name )
		try:
			return attr[i]
		except TypeError:
			# For traversability purposes, we also accept
			# our string names as assigned in append
			# This could also be done with an adapter
			try:
				return attr[int(i)]
			except ValueError: # can't convert to int
				raise KeyError( i )

	return __getitem__
