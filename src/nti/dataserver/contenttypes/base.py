#!/usr/bin/env python
"""
Base functionality.
"""
from __future__ import print_function, unicode_literals

import persistent
import collections


from nti.externalization.externalization import stripSyntheticKeysFromExternalDictionary
from nti.externalization.externalization import to_external_object
from nti.externalization.internalization import update_from_external_object

from nti.dataserver import datastructures
from nti.dataserver import mimetype
from nti.dataserver import sharing
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import users
from nti.ntiids import ntiids

from zope import interface
from zope import component
from zope.deprecation import deprecate

def _get_entity( username, dataserver=None ):
	return users.Entity.get_entity( username, dataserver=dataserver, _namespace=users.User._ds_namespace )


# TODO: These objects should probably implement IZContained (__name__,__parent__). Otherwise they
# often wind up wrapped in container proxy objects, which is confusing. There may be
# traversal implications to that though, that need to be considered. See also classes.py
@interface.implementer(nti_interfaces.IModeledContent)
class UserContentRoot(sharing.ShareableMixin, datastructures.ContainedMixin, datastructures.CreatedModDateTrackingObject, persistent.Persistent):
	"""
	Base implementation of behaviours expected for contenttypes. Should be the primary
	superclass for subclasses.

	Subclasses must arrange for there to be an implementation of ``toExternalDictionary``.

	"""
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass

	#: It is allowed to create instances of these classes from
	#: external data.
	__external_can_create__ = True

	def __init__(self):
		super(UserContentRoot,self).__init__()

	__ext_ignore_toExternalObject__ = True
	@deprecate("Prefer to use nti.externalization directly.")
	def toExternalObject( self ):
		return to_external_object( self )

	__ext_ignore_updateFromExternalObject__ = True
	@deprecate("Prefer to use nti.externalization directly.")
	def updateFromExternalObject( self, ext_object, context=None ):
		return update_from_external_object( self, ext_object, context=context )

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

from nti.externalization.interfaces import IInternalObjectIO
from nti.externalization.datastructures import ExternalizableInstanceDict
from zope.proxy import removeAllProxies

@component.adapter(nti_interfaces.IModeledContent)
@interface.implementer(IInternalObjectIO)
class UserContentRootInternalObjectIO(ExternalizableInstanceDict):

	#: By default, if an update comes in with only new sharing information,
	#: and we have been previously saved, then we do not clear our
	#: other contents. Subclasses can override this by setting canUpdateSharingOnly
	#: to ``False``.
	canUpdateSharingOnly = True

	def __init__( self, context ):
		super(UserContentRootInternalObjectIO,self).__init__()
		self.context = context

	def _ext_replacement(self):
		# TODO: The intid utility doesn't find objects if they are proxied. It unwraps
		# the security proxy, but we (the appserver) may be putting an Uncached proxy around them.
		# A further problem is that for our __dict__ based IO, this fails miserably to get
		# all the attributes, because the proxy has its own __dict__, it seems
		# So we are unwrapping that here. Who should really be doing that?
		# TODO: This could break externalization triggered off interfaces added with a proxy
		# See also chatserver.messageinfo.
		return removeAllProxies(self.context)

	def toExternalObject( self, mergeFrom=None ):
		extDict = super(UserContentRootInternalObjectIO,self).toExternalObject(mergeFrom=mergeFrom)
		extDict['sharedWith'] = self.context.sharedWith
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
		return len(parsed) == 0 and self.canUpdateSharingOnly and self.context._p_jar

	def _update_sharing_targets( self, sharedWith ):
		# Replace sharing with the incoming data.

		targets = set()
		for s in sharedWith or ():
			target = s
			if _get_entity( s ):
				target = _get_entity( s )
			elif hasattr( self.context.creator, 'getFriendsList' ):
				# This branch is semi-deprecated. They should send in
				# the NTIID of the list...once we apply security here
				target = self.context.creator.getFriendsList( s )

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
					if self.context.creator in ents:
						ents.discard( self.context.creator ) # don't let the creator slip in there
						target = tuple(ents)


			# We only add target, and only if it is non-none and
			# resolver. Otherwise we are falsely implying sharing
			# happened when it really didn't
			if target is not s and target is not None:
				targets.add( target or s )
		self.context.updateSharingTargets( targets )

	def updateFromExternalObject( self, ext_parsed, *args, **kwargs ):
		assert isinstance( ext_parsed, collections.Mapping )
		parsed = ext_parsed
		# The pattern for subclasses is to pop the things that need special, non-dict handling,
		# and then to call super. When super returns, handle the special case
		sharedWith = parsed.pop( 'sharedWith', () )


		if self._is_update_sharing_only( parsed ):
			# In this state, we have received an update only for sharing.
			# and so do not need to do anything else. We're a saved
			# object already. If we're not saved already, we cannot
			# be created with just this
			pass
#		elif len(stripSyntheticKeysFromExternalDictionary( dict( parsed ) )) == 0:
#			raise ValueError( "Updating non-saved object: The body must have some data, cannot be empty" )

		self.context.updateLastMod()
		super(UserContentRootInternalObjectIO,self).updateFromExternalObject( parsed, *args, **kwargs )

		self._update_sharing_targets( sharedWith )
