#!/usr/bin/env python2.7
"""
ACL providers for the various content types.
"""

from zope import interface
from zope import component
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import authorization as auth

class _ACE(object):
	"""
	Object to hold a single ACE, permitting more descriptive code.
	"""

	@classmethod
	def allowing( cls, actor=None, permission=None ):
		"""
		:return: An :class:`nti_interfaces.IACE` allowing the given `actor` the given `permission.`

		:param actor: The :class:`nti_interfaces.IPrincipal` being given the permission.
			Must be an `IPrincipal` or something that can be converted to it.
		:param permission: The :class:`nti_interfaces.IPermission` being given.
			Must be an `IPermission` or something that can be converted to it,
			or an interable sequence thereof. Also allowable is :const:`nti_interfaces.ALL_PERMISSIONS`.
		"""
		return cls( nti_interfaces.ACE_ACT_ALLOW, actor, permission )

	@classmethod
	def denying( cls, actor=None, permission=None ):
		"""
		:return: An :class:`nti_interfaces.IACE` denying the given `actor` the given `permission.`

		:param actor: The :class:`nti_interfaces.IPrincipal` being denied the permission.
			Must be an `IPrincipal` or something that can be converted to it.
		:param permission: The :class:`nti_interfaces.IPermission` being denied.
			Must be an `IPermission` or something that can be converted to it,
			or an interable sequence thereof. Also allowable is :const:`nti_interfaces.ALL_PERMISSIONS`.
		"""
		return cls( nti_interfaces.ACE_ACT_DENY, actor, permission )

	def __init__( self, action, actor, permission ):
		self.action = action
		assert self.action in (nti_interfaces.ACE_ACT_ALLOW,nti_interfaces.ACE_ACT_DENY)
		self.actor = (nti_interfaces.IPrincipal( actor )
						if not nti_interfaces.IPrincipal.providedBy( actor )
						else actor)
		if not hasattr( permission, '__iter__' ):
			permission = [permission]

		if permission is nti_interfaces.ALL_PERMISSIONS:
			self.permission = permission
		else:
			self.permission = [(component.queryUtility(nti_interfaces.IPermission, x)
								if not nti_interfaces.IPermission.providedBy(x)
								else x)
								for x
								in permission]

	def __eq__(self,other):
		# TODO: Work on this
		return self.action == other.action and self.actor == other.actor and self.permission == other.permission

	def __iter__(self):
		return iter( (self.action, self.actor, self.permission) )

	def __repr__(self):
		return "%s('%s',%s,%s)" % (self.__class__.__name__,
								   self.action,
								   self.actor,
								   self.permission)

# Export these ACE functions publicly
ace_allowing = _ACE.allowing
ace_denying = _ACE.denying

def ACL( obj, default=() ):
	"""
	Produce an ACL for the given `obj`. If the object already has an ACL,
	that will be returned. Otherwise, if it can be adapted into
	an :class:`IACLProvider` it will be and that will be returned.
	If no ACL can be found, returns an empty iterable (or whatever
	the value of the `default` parameter is).
	"""
	try:
		return obj.__acl__
	except AttributeError:
		try:
			return nti_interfaces.IACLProvider( obj ).__acl__
		except TypeError:
			return default

class _CreatedACLProvider(object):
	"""
	The creator of an object can do anything with it.
	"""

	interface.implements( nti_interfaces.IACLProvider )
	component.adapts( nti_interfaces.ICreated )

	def __init__( self, created ):
		self._created = created

	def _creator_acl( self ):
		"""
		:return: A fresh, mutable list containing at most one :class:`_ACE` for
				the creator (if there is a creator).
		"""
		return ([_ACE.allowing( self._created.creator, nti_interfaces.ALL_PERMISSIONS )]
				if getattr(self._created, 'creator', None ) # They don't all comply with the interface
				else [])

	@property
	def __acl__( self ):
		"""
		:return: A fresh, mutable list containing at exactly two :class:`_ACE` for
				the creator (if there is a creator), and one denying all rights to everyone else.
		"""
		acl = self._creator_acl( )
		acl.append( nti_interfaces.ACE_DENY_ALL )
		return acl


class _ShareableModeledContentACLProvider(_CreatedACLProvider):
	"""
	Things that are shared can be viewed by those they are
	shared with.
	"""

	interface.implements( nti_interfaces.IACLProvider )
	component.adapts( nti_interfaces.IShareableModeledContent )

	def __init__( self, obj ):
		super(_ShareableModeledContentACLProvider, self).__init__( obj )

	@property
	def __acl__( self ):
		result = self._creator_acl()
		for name in self._created.getFlattenedSharingTargetNames():
			result.append( _ACE.allowing( name, auth.ACT_READ ) )
		return result

# NOTE: All of the ACLs around classes will change as
# roles become more defined. E.g., TAs will have some access.

def _provider_admin_ace( obj ):
	localname = str(obj.Provider).split('@')[0]
	return ace_allowing( 'role:' + localname + '.Admin', nti_interfaces.ALL_PERMISSIONS )

class _SectionInfoACLProvider(_CreatedACLProvider):
	"""
	Class sections are viewable by those enrolled in the section;
	the creator and instructors of the section have full write access.
	"""

	interface.implements( nti_interfaces.IACLProvider )
	component.adapts( nti_interfaces.ISectionInfo )

	def __init__( self, obj ):
		super(_SectionInfoACLProvider,self).__init__(obj)

	@property
	def __acl__(self):
		result = self._creator_acl()
		# First, give the user's enrolled viewing
		for name in self._created.Enrolled:
			result.append( ace_allowing( name, auth.ACT_READ ) )
		# And the instructors get full control
		for name in (self._created.InstructorInfo or ()).Instructors:
			result.append( ace_allowing( name, nti_interfaces.ALL_PERMISSIONS ) )
		# As do the admins
		if self._created.Provider:
			result.append( _provider_admin_ace( self._created ) )
		# And finally nobody else gets jack squat
		result.append( ace_denying( nti_interfaces.EVERYONE_GROUP_NAME, nti_interfaces.ALL_PERMISSIONS ) )
		return result

class _ClassInfoACLProvider(_CreatedACLProvider):
	"""
	Classes are viewable by anyone enrolled in any section;
	the creator and instructors of all sections have full
	write access; admins of the providing organization have full access.
	(Obviously this will change.)
	"""
	component.adapts( nti_interfaces.IClassInfo )

	def __init__( self, obj ):
		super(_ClassInfoACLProvider,self).__init__(obj)

	@property
	def __acl__(self):
		# We assume that a given username
		# will not occur with contradictory rights,
		# since we're only dealing with viewing and everything else.
		# We can thus flatten the acls into a simple dictionary.
		section_acls = dict()
		for s in self._created.Sections:
			acl = ACL(s)
			for ace in acl:
				section_acls[ace.actor] = ace
		# The provider's admin role gets all perms
		if self._created.Provider:
			ace = _provider_admin_ace( self._created )
			section_acls[ace.actor] = ace

		result = self._creator_acl()
		if result:
			# We assume that the creator shows up in what we found.
			# Replace that with the all-access right given
			# by the superclass
			section_acls[result[0].actor] = result[0]
		section_acls.pop( nti_interfaces.IPrincipal(nti_interfaces.EVERYONE_GROUP_NAME), None )
		result = [v for v in section_acls.values()]
		# And finally nobody else gets jack squat
		result.append( ace_denying( nti_interfaces.EVERYONE_GROUP_NAME, nti_interfaces.ALL_PERMISSIONS ) )

		return result

class _EnclosedContentACLProvider(_CreatedACLProvider):
	"""
	The ACL for enclosed content depends on a few things, most notably
	whether the content it is enclosing itself has an ACL.
	"""
	component.adapts( nti_interfaces.IEnclosedContent )

	def __init__( self, obj ):
		super(_EnclosedContentACLProvider,self).__init__( obj )

	@property
	def __acl__( self ):
		# Give the creator full rights.
		result = self._creator_acl()
		# Add to this any ACL we can determine for the enclosed
		# content
		result.extend( ACL( self._created.data ) )
		return result

class _LibraryTOCEntryACLProvider(object):
	"""
	Allows all authenticated users access to library entries.
	"""
	interface.implements( nti_interfaces.IACLProvider )
	component.adapts(nti_interfaces.ILibraryTOCEntry)

	def __init__( self, obj ):
		self._obj = obj
		self.__acl__ = ( ace_allowing( nti_interfaces.AUTHENTICATED_GROUP_NAME, nti_interfaces.ALL_PERMISSIONS ), )
