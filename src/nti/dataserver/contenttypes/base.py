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

from nti.utils.property import alias

from zope import interface
from zope import component
from zope.deprecation import deprecate

def _get_entity( username, dataserver=None ):
	return users.Entity.get_entity( username, dataserver=dataserver, _namespace=users.User._ds_namespace )


@interface.implementer(nti_interfaces.IModeledContent)
class UserContentRoot(sharing.ShareableMixin, datastructures.ZContainedMixin, datastructures.CreatedModDateTrackingObject, persistent.Persistent):
	"""
	Base implementation of behaviours expected for contenttypes. Should be the primary
	superclass for subclasses.

	Subclasses must arrange for there to be an implementation of ``toExternalDictionary``.

	"""
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass

	#: It is allowed to create instances of these classes from
	#: external data.
	__external_can_create__ = True

	__name__ = alias('id') # this was previously at SelectedRange, but everything extends SelectedRange

	# TODO: Define containerId as an alias for __parent__.__name__ ? Right now they are completely separate,
	# and the __parent__ relationship is in fact initially established by the setting of containerId
	# in incoming data

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
from nti.externalization.datastructures import InterfaceObjectIO
from nti.utils.proxy import removeAllProxies


class UserContentRootInternalObjectIOMixin(object):

	validate_after_update = True

	# NOTE: inReplyTo and 'references' do not really belong here
	_excluded_out_ivars_ = { 'flattenedSharingTargetNames', 'flattenedSharingTargets', 'sharingTargets', 'inReplyTo', 'references' } | InterfaceObjectIO._excluded_out_ivars_

	context = alias('_ext_self')
	_orig_sharingTargets = None # a cache for holding the targets before we update them

	def _ext_replacement(self):
		# TODO: The intid utility doesn't find objects if they are proxied. It unwraps
		# the security proxy, but we (the appserver) may be putting an Uncached proxy around them.
		# So we are unwrapping that here. Who should really be doing that?
		# TODO: This could break externalization triggered off interfaces added with a proxy
		# See also chatserver.messageinfo.
		return removeAllProxies(self.context)

	def toExternalObject( self, mergeFrom=None ):
		extDict = super(UserContentRootInternalObjectIOMixin,self).toExternalObject(mergeFrom=mergeFrom)
		extDict['sharedWith'] = getattr( self.context, 'sharedWith', () ) # optional
		return extDict

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
		sharedWith = parsed.pop( 'sharedWith', self )

		self.context.updateLastMod()
		super(UserContentRootInternalObjectIOMixin,self).updateFromExternalObject( parsed, *args, **kwargs )

		if nti_interfaces.IWritableShared.providedBy( self.context ) and sharedWith is not self:
			self._orig_sharingTargets = set(self.context.sharingTargets)
			self._update_sharing_targets( sharedWith )

	def _ext_adjust_modified_event( self, event ):
		if self._orig_sharingTargets is not None:
			# Yes, we attempted to change the sharing settings.
			interface.alsoProvides( event, nti_interfaces.IObjectSharingModifiedEvent )
			event.oldSharingTargets = self._orig_sharingTargets
		return event

@interface.implementer(IInternalObjectIO)
class UserContentRootInternalObjectIO(UserContentRootInternalObjectIOMixin,InterfaceObjectIO):

	_ext_iface_upper_bound = nti_interfaces.IModeledContent

#	_excluded_out_ivars_ = { 'flattenedSharingTargetNames', 'flattenedSharingTargets', 'sharingTargets', 'inReplyTo', 'references' } | InterfaceObjectIO._excluded_out_ivars_

	def __init__( self, context ):
		super(UserContentRootInternalObjectIO,self).__init__(context)
