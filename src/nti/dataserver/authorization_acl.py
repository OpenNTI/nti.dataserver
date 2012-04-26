#!/usr/bin/env python2.7
"""
ACL providers for the various content types.
"""

from __future__ import unicode_literals, print_function

import logging
logger = logging.getLogger(__name__)

import six
import os

from zope import interface
from zope import component

import pyramid.security
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import authorization as auth
from nti.externalization import interfaces as ext_interfaces

class _ACE(object):
	"""
	Object to hold a single ACE, permitting more descriptive code and
	prettier string output. These objects must not be persisted.
	"""

	interface.implements( nti_interfaces.IACE )

	@classmethod
	def allowing( cls, actor=None, permission=None, provenance=None ):
		"""
		:return: An :class:`nti_interfaces.IACE` allowing the given `actor` the given `permission.`

		:param actor: The :class:`nti_interfaces.IPrincipal` being given the permission.
			Must be an `IPrincipal` or something that can be converted to it.
		:param permission: The :class:`nti_interfaces.IPermission` being given.
			Must be an `IPermission` or something that can be converted to it,
			or an interable sequence thereof. Also allowable is :const:`nti_interfaces.ALL_PERMISSIONS`.
		:param provenance: A string or :class:`type` giving information about where this entry came from.
		"""
		return cls( nti_interfaces.ACE_ACT_ALLOW, actor, permission, provenance=provenance )

	@classmethod
	def denying( cls, actor=None, permission=None, provenance=None ):
		"""
		:return: An :class:`nti_interfaces.IACE` denying the given `actor` the given `permission.`

		:param actor: The :class:`nti_interfaces.IPrincipal` being denied the permission.
			Must be an `IPrincipal` or something that can be converted to it.
		:param permission: The :class:`nti_interfaces.IPermission` being denied.
			Must be an `IPermission` or something that can be converted to it,
			or an interable sequence thereof. Also allowable is :const:`nti_interfaces.ALL_PERMISSIONS`.
		:param provenance: A string or :class:`type` giving information about where this entry came from.
		"""
		return cls( nti_interfaces.ACE_ACT_DENY, actor, permission, provenance=provenance )

	@classmethod
	def from_external_string( cls, string, provenance='from_string' ):
		parts = string.split( ':' )
		assert len(parts) == 3
		action = parts[0]
		actor = parts[1]

		perms = parts[2]
		if perms == 'All':
			perms = nti_interfaces.ALL_PERMISSIONS
		else:
			# trim the surrounding array chars
			perms = perms[1:-1]
			perms = [x.strip().strip("'") for x in perms.split(',')]

		return cls( action, actor, perms, provenance=provenance )

	_provenance = None

	def __init__( self, action, actor, permission, provenance=None ):
		self.action = action
		assert self.action in (nti_interfaces.ACE_ACT_ALLOW,nti_interfaces.ACE_ACT_DENY)
		self.actor = (nti_interfaces.IPrincipal( actor )
						if not nti_interfaces.IPrincipal.providedBy( actor )
						else actor)
		if not hasattr( permission, '__iter__' ):
			permission = [permission]

		if provenance:
			self._provenance = provenance

		if permission is nti_interfaces.ALL_PERMISSIONS:
			self.permission = permission
		else:
			self.permission = [(component.queryUtility(nti_interfaces.IPermission, x)
								if not nti_interfaces.IPermission.providedBy(x)
								else x)
								for x
								in permission]
			self.permission = [x for x in self.permission if x is not None]
			assert self.permission, "Must provide a permission"

	# Make them non-picklable
	def __reduce__( self, *args, **kwargs ):
		raise TypeError( "ACEs cannot be pickled." )
	__reduce_ex__ = __reduce__

	def to_external_string(self):
		"""
		:return: A string representing this ACE in a form that can be read
		by :meth:`from_external_string`
		"""
		return "%s:%s:%s" % (self.action,
							 self.actor.id,
							 'All' if self.permission is nti_interfaces.ALL_PERMISSIONS else [str(x.id) for x in self.permission])


	def __eq__(self,other):
		# TODO: Work on this
		# This trick (reversing the order and comparing to a tuple) lets us compare
		# equal to plain tuples as used in pyramid and that sometimes sneak in
		return other == (self.action, self.actor.id, self.permission)

	def __iter__(self):
		return iter( (self.action, self.actor, self.permission) )

	def __repr__(self):
		provenance = ''
		if self._provenance:
			provenance = self._provenance.__name__ if isinstance(self._provenance,type) else type(self._provenance).__name__
		return "<%s: %s,%s,%s%s>" % (self.__class__.__name__,
									 self.action,
									 self.actor.id,
									 getattr( self.permission, 'id', self.permission ),
									 (" := " + provenance if provenance else '' ) )

# Export these ACE functions publicly
ace_allowing = _ACE.allowing
ace_denying = _ACE.denying
ace_from_string = _ACE.from_external_string

def acl_from_file( path_or_file ):
	"""
	Return an ACL parsed from reading the contents of the given file.
	:param path_or_file: Either a string giving a path to a readable file,
		or a file-like object supporting :meth:`file.readlines`.
	"""
	if isinstance(path_or_file, six.string_types):
		with open(path_or_file, 'rU') as f:
			lines = f.readlines()
			provenance = path_or_file
	else:
		lines = path_or_file.readlines()
		provenance = getattr( path_or_file, 'name', str(path_or_file) )

	return _ACL( [ace_from_string(x.strip(),provenance=provenance) for x in lines] )

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

def has_permission( permission, context, username, **kwargs ):
	"""
	Checks to see if the user named by ``username`` has been
	allowed the ``permission`` on (or in) the ``context``.

	:param permission: A string or :class:`nti_interfaces.IPermission` object to check
	:param context: An object that the :func:`ACL` function can get an ACL for.
	:param username: A user object or username designating a user that :func:`auth.effective_principals`
		can turn into a set of principals. Additional keyword arguments are passed to this
		function.
	:return: An object that behaves like a boolean value but provides a description
		about what was allowed or denied when printed.

	"""

	try:
		context.__acl__
	except AttributeError:
		try:
			to_check = nti_interfaces.IACLProvider( context )
		except TypeError:
			return pyramid.security.Denied( "No ACL found" )
	else:
		to_check = context


	policy = component.queryUtility(nti_interfaces.IAuthorizationPolicy)
	if not policy:
		return pyramid.security.Denied( "No IAuthorizationPolicy installed" )
	return policy.permits( to_check,
						   auth.effective_principals( username, **kwargs ),
						   permission )


class ACLDecorator(object):
	interface.implements(ext_interfaces.IExternalMappingDecorator)
	component.adapts(object)

	def __init__( self, o ):
		pass

	def decorateExternalMapping( self, orig, result ):
		result.__acl__ = ACL( orig )

class _ACL(list):
	interface.implements(nti_interfaces.IACL)

	def write_to_file( self, path_or_file ):
		"""
		Given a path to a writable file or a file-like object (having the `write` method),
		writes each entry in this ACL to the file.
		:return: None
		"""
		def _write(f):
			for x in self:
				f.write( x.to_external_string() )
				f.write( '\n' )
		if isinstance(path_or_file, six.string_types):
			with open(path_or_file, 'w') as f:
				_write(f)
		else:
			_write( path_or_file )


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
		return _ACL([ace_allowing( self._created.creator, nti_interfaces.ALL_PERMISSIONS, self )]
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
			result.append( ace_allowing( name, auth.ACT_READ, _ShareableModeledContentACLProvider ) )
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
			result.append( ace_allowing( name, auth.ACT_READ, _SectionInfoACLProvider ) )
		# And the instructors get full control
		for name in (self._created.InstructorInfo or ()).Instructors:
			result.append( ace_allowing( name, nti_interfaces.ALL_PERMISSIONS, _SectionInfoACLProvider ) )
		# As do the admins
		if self._created.Provider:
			result.append( _provider_admin_ace( self._created ) )
		# And finally nobody else gets jack squat
		result.append( ace_denying( nti_interfaces.EVERYONE_GROUP_NAME, nti_interfaces.ALL_PERMISSIONS, _SectionInfoACLProvider ) )
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
		result.append( ace_denying( nti_interfaces.EVERYONE_GROUP_NAME, nti_interfaces.ALL_PERMISSIONS, _ClassInfoACLProvider ) )

		return _ACL(result)

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
		# TODO: Should this be taking into account a parent LibraryEntryACLProvider at all?
		# If so, how?
		self.__acl__ = ( ace_allowing( nti_interfaces.AUTHENTICATED_GROUP_NAME, nti_interfaces.ALL_PERMISSIONS, _LibraryTOCEntryACLProvider ), )

class _LibraryEntryACLProvider(object):
	"""
	Checks a library entry for the existence of a '.nti_acl' file, and if present,
	reads an ACL from it. Otherwise, the ACL allows all authenticated
	users access.
	"""
	interface.implements( nti_interfaces.IACLProvider )
	component.adapts( nti_interfaces.ILibraryEntry )

	def __init__( self, obj ):
		self._obj = obj
		if os.path.exists( os.path.join( obj.localPath, '.nti_acl' ) ):
			try:
				self.__acl__ = acl_from_file( os.path.join( obj.localPath, '.nti_acl' ) )
			except:
				logger.exception( "Failed to read acl from %s; denying all access.", obj )
				self.__acl__ = _ACL( (ace_denying( nti_interfaces.EVERYONE_GROUP_NAME, nti_interfaces.ALL_PERMISSIONS, _LibraryEntryACLProvider ), ) )
		else:
			self.__acl__ = _ACL( (ace_allowing( nti_interfaces.AUTHENTICATED_GROUP_NAME, nti_interfaces.ALL_PERMISSIONS, _LibraryTOCEntryACLProvider ), ) )


class _FriendsListACLProvider(_CreatedACLProvider):
	"""
	Makes friends lists readable by those it contains.
	"""
	component.adapts(nti_interfaces.IFriendsList)

	def __init__( self, obj ):
		super(_FriendsListACLProvider,self).__init__( obj )

	@property
	def __acl__( self ):
		result = self._creator_acl()
		for friend in self._created:
			result.append( ace_allowing( friend.username, auth.ACT_READ ) )
		# And finally nobody else gets jack squat
		result.append( ace_denying( nti_interfaces.EVERYONE_GROUP_NAME, nti_interfaces.ALL_PERMISSIONS, _SectionInfoACLProvider ) )
		return result
