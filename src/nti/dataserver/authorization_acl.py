#!/usr/bin/env python
"""
ACL providers for the various content types.
"""

from __future__ import unicode_literals, print_function, absolute_import

import logging
logger = logging.getLogger(__name__)

import six
import codecs

from zope import interface
from zope import component

from zope.cachedescriptors.property import Lazy

import pyramid.security

from nti.utils.property import alias
from nti.ntiids import ntiids

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import authorization
from nti.dataserver import authentication
from nti.contentlibrary import interfaces as content_interfaces
from nti.externalization import interfaces as ext_interfaces

from nti.dataserver import traversal
from nti.externalization.singleton import SingletonDecorator

@interface.implementer( nti_interfaces.IACE )
class _ACE(object):
	"""
	Object to hold a single ACE, permitting more descriptive code and
	prettier string output.

	These objects are persisted in their string forms.
	"""

	@classmethod
	def allowing( cls, actor=None, permission=None, provenance=None ):
		"""
		:return: An :class:`.IACE` allowing the given `actor` the given `permission.`

		:param actor: The :class:`.IPrincipal` being given the permission.
			Must be an `IPrincipal` or something that can be converted to it.
		:param permission: The :class:`.IPermission` being given.
			Must be an `IPermission` or something that can be converted to it,
			or an interable sequence thereof. Also allowable is :const:`.ALL_PERMISSIONS`.
		:param provenance: A string or :class:`type` giving information about where this entry came from.
		"""
		return cls( nti_interfaces.ACE_ACT_ALLOW, actor, permission, provenance=provenance )

	@classmethod
	def denying( cls, actor=None, permission=None, provenance=None ):
		"""
		:return: An :class:`.IACE` denying the given `actor` the given `permission.`

		:param actor: The :class:`.IPrincipal` being denied the permission.
			Must be an `IPrincipal` or something that can be converted to it.
		:param permission: The :class:`.IPermission` being denied.
			Must be an `IPermission` or something that can be converted to it,
			or an interable sequence thereof. Also allowable is :const:`.ALL_PERMISSIONS`.
		:param provenance: A string or :class:`type` giving information about where this entry came from.
		"""
		return cls( nti_interfaces.ACE_ACT_DENY, actor, permission, provenance=provenance )

	@classmethod
	def from_external_string( cls, string, provenance='from_string' ):
		parts = string.split( ':' )
		__traceback_info__ = parts, string, provenance
		# It happens that we use a : to delimit parts, but that is a valid character
		# to use in a role name. We arbitrarily decide that it is not a valid character
		# to use in a permission string. This lets us take the first part as the action
		# the last part as the permission, and any parts in the middle are joined back up
		# by colons to form the actor
		assert len(parts) >= 3
		action = parts[0]
		actor = ':'.join( parts[1:-1] )

		perms = parts[-1]
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
			self.permission = [(component.getUtility(nti_interfaces.IPermission, x) # permissions MUST be named utilities
								if not nti_interfaces.IPermission.providedBy(x)
								else x)
								for x
								in permission]
			assert self.permission, "Must provide a permission"

	def __getstate__( self ):
		return self.to_external_string()
	def __setstate__( self, state ):
		other = self.from_external_string( state, provenance='from pickle' )
		self.__dict__ = other.__dict__

	def to_external_string(self):
		"""
		Returns a string representing this ACE in a form that can be read
		by :meth:`from_external_string`
		"""
		return "%s:%s:%s" % (self.action,
							 self.actor.id,
							 'All' if self.permission is nti_interfaces.ALL_PERMISSIONS else [str(x.id) for x in self.permission])

	def __eq__(self,other):
		# TODO: Work on this
		# This trick (reversing the order and comparing to a tuple) lets us compare
		# equal to plain tuples as used in pyramid and that sometimes sneak in
		try:
			return other == (self.action, self.actor.id, self.permission)
		except AttributeError:
			return NotImplemented

	def __iter__(self):
		return iter( (self.action, self.actor, self.permission) )

	def __repr__(self):
		provenance = ''
		if self._provenance:
			if isinstance( self._provenance, six.string_types ):
				provenance = self._provenance
			elif isinstance( self._provenance, type ):
				provenance = self._provenance.__name__
			else:
				provenance = type(self._provenance).__name__
		return "<%s: %s,%s,%s%s>" % (self.__class__.__name__,
									 self.action,
									 self.actor.id,
									 getattr( self.permission, 'id', self.permission ),
									 (" := " + provenance if provenance else '' ) )

def _ace_denying_all( provenance=None ):
	return _ACE( *(nti_interfaces.ACE_DENY_ALL + (provenance,) ) )
def _ace_allowing_all( provenance=None ):
	return _ACE( *(nti_interfaces.ACE_ALLOW_ALL + (provenance,) ) )

# Export these ACE functions publicly
ace_allowing = _ACE.allowing
ace_denying = _ACE.denying
ace_from_string = _ACE.from_external_string
ace_denying_all = _ace_denying_all
ace_allowing_all = _ace_allowing_all


def acl_from_file( path_or_file ):
	"""
	Return an ACL parsed from reading the contents of the given file.

	:param path_or_file: Either a string giving a path to a readable file,
		or a file-like object supporting :meth:`file.readlines`. Each non-blank,
		non-commented (has a leading #) line will be parsed as an ace using :func:`ace_from_string`.
	"""
	if isinstance(path_or_file, six.string_types):
		with codecs.open(path_or_file, 'rU', encoding='utf-8') as f:
			lines = f.readlines()
			provenance = path_or_file
	else:
		lines = path_or_file.readlines()
		provenance = getattr( path_or_file, 'name', str(path_or_file) )

	return _acl_from_ace_lines( lines, provenance )

def _acl_from_ace_lines( lines, provenance ):
	return _ACL( [ace_from_string(x.strip(), provenance=provenance)
				  for x in lines
				  if x and x.strip() and not x.strip().startswith( '#' )] )

def ACL( obj, default=() ):
	"""
	Produce an ACL for the given `obj`. If the object already has an ACL,
	that will be returned. Otherwise, if it can be adapted into
	an :class:`.IACLProvider` it will be and that will be returned.
	If no ACL can be found, returns an empty iterable (or whatever
	the value of the `default` parameter is).
	"""
	prov = ACLProvider( obj )
	return prov.__acl__ if prov is not None else default


def ACLProvider( obj, default=None ):
	"""
	Produce an ACL provider for the given `obj`. If the object already has an ACL,
	the object is its own provider. Otherwise, if it can be adapted into
	an :class:`.IACLProvider` it will be and that will be returned.
	If no ACL provider can be found, returns None (or whatever
	the value of the `default` parameter is).
	"""
	try:
		return obj.__acl__ is not None and obj
	except AttributeError:
		try:
			return nti_interfaces.IACLProvider( obj )
		except TypeError:
			return default

def has_permission( permission, context, username, **kwargs ):
	"""
	Checks to see if the user named by ``username`` has been
	allowed the ``permission`` on (or in) the ``context``.

	:param permission: A string or :class:`.interfaces.IPermission` object to check
	:param context: An object that the :func:`ACL` function can get an ACL for.
	:param username: A user object or username designating a user that :func:`.authentication.effective_principals`
		can turn into a set of principals. Additional keyword arguments are passed to this
		function.
	:param kwargs: Keyword arguments passed to :func:`.authentication.effective_principals`.


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
						   authentication.effective_principals( username, **kwargs ),
						   permission )

def is_writable( context, username, **kwargs ):
	"""
	Is the ``context`` object writable by the ``username``? The ``context`` object should
	generally not be an already-externalized object.

	A shortcut to :func:``has_permission``; see its docs for details.
	"""

	return has_permission( authorization.ACT_UPDATE, context, username, **kwargs )

from ZODB.POSException import POSKeyError

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(object)
class ACLDecorator(object):
	__metaclass__ = SingletonDecorator

	def decorateExternalMapping( self, orig, result ):
		try:
			result.__acl__ = ACL( orig )
		except POSKeyError:
			logger.warn( "Failed to get ACL on POSKeyError" )
			result.__acl__ = ()

@interface.implementer(nti_interfaces.IACL)
class _ACL(list):

	def __add__( self, other ):
		"We allow concatenating single ACE objects to an ACL to produce a new ACL"
		if isinstance( other, _ACE ):
			result = _ACL( self )
			result.append( other )
			return result
		return super(_ACL,self).__add__( other )

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
			with codecs.open(path_or_file, 'w', encoding='utf-8') as f:
				_write(f)
		else:
			_write( path_or_file )

def acl_from_aces( *args ):
	"""
	Create an ACL from ACEs.
	Can either provide a list of ACEs, or var-args that are individual ACEs.
	"""
	if len(args) == 1:
		if isinstance(args[0],_ACE):
			return _ACL( (args[0],) )
		return _ACL( args[0] )

	return _ACL( args )

class _LazyOnClass(object):
	"""
	Like :class:`zope.cachedescriptors.property.Lazy`, but
	when it caches, it caches on the class itself, not the instance,
	thus sharing the value. Thus, the value should be immutable and
	independent of any other state.
	"""

	def __init__( self, func ):
		self._func = func
		self.klass_cache_name = '_v__LazyOnClass_' + self._func.__name__

	def __get__( self, inst, klass ):
		if inst is None:
			return self

		# In order to let this be resetable, to keep access
		# to this object and the original function, we
		# use a different name
		klass_cache_name = self.klass_cache_name
		val = getattr( klass, klass_cache_name, self )
		if val is self:
			val = self._func(inst)
			setattr( klass, klass_cache_name, val )
		return val

def _add_admin_moderation( acl, provenance ):
	acl.append( ace_allowing( authorization.ROLE_MODERATOR, authorization.ACT_MODERATE, provenance ) )
	acl.append( ace_allowing( authorization.ROLE_ADMIN, authorization.ACT_MODERATE, provenance ) )
	acl.append( ace_allowing( authorization.ROLE_ADMIN, authorization.ACT_COPPA_ADMIN, provenance ) )


@interface.implementer(nti_interfaces.IACLProvider)
@component.adapter(nti_interfaces.IEntity)
class _EntityACLProvider(object):
	"""
	ACL provider for class:`.interfaces.IEntity` objects. The
	entity itself is allowed all permissions.
	"""
	# TODO: Extend this for other subclasses such as communities?
	# Define 'roles' and make Users members of roles that represent
	# their community

	_DENY_ALL = True

	def __init__( self, entity ):
		self._entity = entity

	def _viewers(self):
		return ( nti_interfaces.AUTHENTICATED_GROUP_NAME, )

	@Lazy
	def __acl__( self ):
		"""
		The ACL for the entity.

		"""
		acl = _ACL([ace_allowing( self._entity.username, nti_interfaces.ALL_PERMISSIONS, self )])
		for viewer in self._viewers():
			acl.append( ace_allowing( viewer, authorization.ACT_READ, self) )
		_add_admin_moderation( acl, self )
		if self._DENY_ALL:
			# Everyone else can do nothing
			acl.append( _ace_denying_all( _EntityACLProvider ) )
		return acl

@component.adapter(nti_interfaces.IUser)
class _UserACLProvider(_EntityACLProvider):
	"""
	ACL Provider for :class:`.interfaces.IUser`.
	"""

	def _viewers(self):
		# intersecting community members have viewing rights
		# this is a private function while in flux
		return authentication._dynamic_memberships_that_participate_in_security( self._entity )

@component.adapter(nti_interfaces.ICoppaUserWithoutAgreement)
class _CoppaUserWithoutAgreementACLProvider(_UserACLProvider):
	"""
	ACL Provider for Koppa Kids that limits all access to them.
	"""

	def _viewers(self):
		return () # nobody!

@interface.implementer(nti_interfaces.IACLProvider)
@component.adapter(nti_interfaces.ICreated)
class _CreatedACLProvider(object):
	"""
	ACL provider for class:`nti_interfaces.ICreated` objects.
	The creator of an object is allowed all permissions.
	"""

	def __init__( self, created ):
		self._created = created

	context = alias('_created')
	_REQUIRE_CREATOR = False

	def _creator_acl( self ):
		"""
		Creates the ACL for just the creator; subclasses may call.

		:return: A fresh, mutable list containing at most one :class:`_ACE` for
				the creator (if there is a creator).
		"""
		result = _ACL([ace_allowing( self._created.creator, nti_interfaces.ALL_PERMISSIONS, self )]
					if getattr(self._created, 'creator', None ) # They don't all comply with the interface
					else [])
		if self._REQUIRE_CREATOR and len(result) != 1:
			raise ValueError( "Unable to get creator", self._created )
		return result

	@Lazy
	def __acl__( self ):
		"""
		The ACL for the creator.

		:return: A fresh, mutable list containing at exactly two :class:`_ACE` for
				the creator (if there is a creator), and one denying all rights to everyone else.
		"""
		acl = self._creator_acl( )
		acl.append( _ace_denying_all( type(self) ) )
		return acl


class AbstractCreatedAndSharedACLProvider(_CreatedACLProvider):
	"""
	Abstract base class for providing the ACL in the common case of an object that has a creator
	that should have full access plus others that should have read access (the *sharing targets*).
	Subclasses of this class will need to implement :meth:`_get_sharing_target_names`
	to return an iterable of all the sharing target names.

	.. py:attribute:: _DENY_ALL

		Subclasses can set this to ``True`` (default is ``False``) to force explicitly
		denying all access to everyone not otherwise listed as having access.
	"""

	_DENY_ALL = False
	_PERMS_FOR_SHARING_TARGETS = (authorization.ACT_READ,)

	def _get_sharing_target_names(self):
		"""
		Subclasses implement to return an iterable over names (or principals) that should have
		the access given in :data:`_PERMS_FOR_SHARING_TARGETS`. Each element of the returned
		sequence will be adapted to an :class:`nti.dataserver.interfaces.IPrincipal`.
		"""
		raise NotImplementedError() # pragma: no cover

	def __do_get_sharing_target_names(self):
		try:
			return self._get_sharing_target_names()
		except POSKeyError:
			logger.warn( "POSKeyError getting sharing target names.")
			return ()

	def _extend_acl_before_deny( self, acl ):
		"""
		Called after the creator and sharing target acls have been added, but
		before the deny-everyone is added. You can add additional options here.
		"""
		return

	@Lazy
	def __acl__( self ):
		"""
		The ACL for this object. If this class sets :attr:`_DENY_ALL` to ``True`` then everyone
		not explicitly listed is denied any access.
		"""
		result = self._creator_acl()
		for name in self.__do_get_sharing_target_names():
			for perm in self._PERMS_FOR_SHARING_TARGETS:
				result.append( ace_allowing( name, perm, type(self) ) )
		if self._DENY_ALL:
			self._extend_acl_before_deny( result )
			result.append( _ace_denying_all( type(self) ) )
		return result


@component.adapter(nti_interfaces.IShareableModeledContent)
class _ShareableModeledContentACLProvider(AbstractCreatedAndSharedACLProvider):
	"""
	Extends the ACL for :class:`nti.dataserver.interfaces.ICreated` objects to things that
	are shared.

	Those things that are shared can be viewed (:data:`authorization.ACT_READ`) by those they are
	shared with. (When shared with something that can be adapted to :class:`nti.dataserver.interfaces.IUsernameIterable`,
	then the complete list of users is expanded into the ACL; the alternative is to have
	principals appear to be members of all these things, as a group.)

	This is modified: If this object is the child of another :class:`.IReadableShared`
	e.g., a Canvas inside a Note, then the ACL is skipped and just inherited
	from the parent (so traversal must be appropriate and respected in ACL checks). This
	prevents problems when denying all access.
	"""

	_DENY_ALL = True

	def _get_sharing_target_names( self ):
		# By expanding in this way, in certain cases we can get
		# multiple entries for the creator. That's OK, because the creator
		# ACE comes first, and because they are both 'allow' entries
		return self.context.flattenedSharingTargetNames

	def _extend_acl_before_deny( self, acl ):
		# If we're going to deny, admins and moderators still get the right
		# privs (?)
		_add_admin_moderation( acl, self )
		acl.append( ace_allowing( authorization.ROLE_MODERATOR, nti_interfaces.ALL_PERMISSIONS, self ) )
		acl.append( ace_allowing( authorization.ROLE_ADMIN, nti_interfaces.ALL_PERMISSIONS, self ) )

	@Lazy
	def __acl__( self ):
		# Inherit if we are nested. See class comment. NOTE: We are just checking the direct parent,
		# not the entire traversal chain; checking to see if anything we are within is IReadableShared
		# might pull in the wrong permissions, depending on how the nesting goes (?)
		if nti_interfaces.IReadableShared.providedBy( getattr( self.context, '__parent__', None ) ):
			return ()
		return super(_ShareableModeledContentACLProvider,self).__acl__

# NOTE: All of the ACLs around classes will change as
# roles become more defined. E.g., TAs will have some access.

def _provider_admin_ace( obj ):
	localname = str(obj.Provider).split('@')[0]
	return ace_allowing( nti_interfaces.IGroup('role:' + localname + '.Admin'), nti_interfaces.ALL_PERMISSIONS )

@component.adapter(nti_interfaces.ISectionInfo)
class _SectionInfoACLProvider(_CreatedACLProvider):
	"""
	Class sections are viewable by those enrolled in the section;
	the creator and instructors of the section have full write access.
	"""

	def __init__( self, obj ):
		super(_SectionInfoACLProvider,self).__init__(obj)

	@Lazy
	def __acl__(self):
		result = self._creator_acl()
		# First, give the user's enrolled viewing
		for name in self._created.Enrolled:
			result.append( ace_allowing( name, authorization.ACT_READ, _SectionInfoACLProvider ) )
		# And the instructors get full control
		for name in (self._created.InstructorInfo or ()).Instructors:
			result.append( ace_allowing( name, nti_interfaces.ALL_PERMISSIONS, _SectionInfoACLProvider ) )
		# As do the admins
		if self._created.Provider:
			result.append( _provider_admin_ace( self._created ) )
		# And finally nobody else gets jack squat
		result.append( _ace_denying_all( _SectionInfoACLProvider ) )
		return result

@component.adapter( nti_interfaces.IClassInfo )
class _ClassInfoACLProvider(_CreatedACLProvider):
	"""
	Classes are viewable by anyone enrolled in any section;
	the creator and instructors of all sections have full
	write access; admins of the providing organization have full access.
	(Obviously this will change.)
	"""

	def __init__( self, obj ):
		super(_ClassInfoACLProvider,self).__init__(obj)

	@Lazy
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

@component.adapter( nti_interfaces.IEnclosedContent )
class _EnclosedContentACLProvider(_CreatedACLProvider):
	"""
	The ACL for enclosed content depends on a few things, most notably
	whether the content it is enclosing itself has an ACL.
	"""

	def __init__( self, obj ):
		super(_EnclosedContentACLProvider,self).__init__( obj )

	@Lazy
	def __acl__( self ):
		# Give the creator full rights.
		result = self._creator_acl()
		# Add to this any ACL we can determine for the enclosed
		# content
		result.extend( ACL( self._created.data ) )
		return result

@interface.implementer( nti_interfaces.IACLProvider )
@component.adapter(content_interfaces.IContentUnit)
class _TestingLibraryTOCEntryACLProvider(object):
 	"""
 	Allows all authenticated users access to library entries.
	This class is for testing only, never for use in a production scenario.
 	"""

	def __init__( self, context ):
 		self.context = context

	@property
	def __parent__( self ):
		return self.context.__parent__

	@_LazyOnClass
	def __acl__(self):
 		return ( ace_allowing( nti_interfaces.AUTHENTICATED_GROUP_NAME, nti_interfaces.ALL_PERMISSIONS, _TestingLibraryTOCEntryACLProvider ), )



# TODO: This could be (and was) registered for a simple IDelimitedHierarchyEntry.
# There is none of that separate from the contentpackage/unit though, so it shouldn't
# be needed in that capacity.
class _AbstractDelimitedHierarchyEntryACLProvider(object):
	"""
	Checks a hierarchy entry for the existence of a file (typically .'.nti_acl'), and if present,
	reads an ACL from it.

	Otherwise, the ACL allows all authenticated users access.
	"""

	def __init__( self, context ):
		self.context = context

	_acl_sibling_entry_name = '.nti_acl'
	_default_allow = True
	_add_default_deny_to_acl_from_file = False

	__parent__ = property(lambda self: self.context.__parent__)

	@Lazy
	def __acl__(self):
		acl_string = self.context.read_contents_of_sibling_entry( self._acl_sibling_entry_name )
		if acl_string is not None:
			try:
				__acl__ = self._acl_from_string(self.context, acl_string )
				# Empty files (those that do exist but feature no valid ACL lines)
				# are considered a mistake, an overlooked accident. In the interest of trying
				# to be secure by default and not allow oversights through, call them out.
				# This results in default-deny
				if not __acl__:
					raise ValueError( "ACL file had no valid contents." )
				if self._add_default_deny_to_acl_from_file:
					__acl__.append( _ace_denying_all( 'Default Deny After File ACL' ) )
			except (ValueError,AssertionError,TypeError):
				logger.exception( "Failed to read acl from %s/%s; denying all access.", self.context, self._acl_sibling_entry_name )
				__acl__ = _ACL( (_ace_denying_all( 'Default Deny Due to Parsing Error' ),) )
		elif self._default_allow:
			__acl__ = _ACL( (ace_allowing( nti_interfaces.AUTHENTICATED_GROUP_NAME, nti_interfaces.ALL_PERMISSIONS, _AbstractDelimitedHierarchyEntryACLProvider ), ) )
		else:
			__acl__ = () # Inherit from parent
		return __acl__

	def _acl_from_string(self, context, acl_string):
		return _acl_from_ace_lines( acl_string.splitlines(), context )



@interface.implementer( nti_interfaces.IACLProvider )
@component.adapter( content_interfaces.IDelimitedHierarchyContentPackage )
class _DelimitedHierarchyContentPackageACLProvider(_AbstractDelimitedHierarchyEntryACLProvider):
	"""
	For content packages that are part of a hierarchy,
	read the ACL file if they have one, and also add read-access to a pseudo-group
	based on the (lowercased) NTIID of the closest containing content package.

	If they have no ACL, then any authenticated user is granted access to the content.

	If they do have an ACL, then we force the last entry to be a global denial. Thus,
	if you specifically want to allow everyone, you must put that in the ACL file.
	"""

	_add_default_deny_to_acl_from_file = True

	def _acl_from_string( self, context, acl_string ):
		acl = super(_DelimitedHierarchyContentPackageACLProvider,self)._acl_from_string( context, acl_string )
		package = traversal.find_interface( context, content_interfaces.IContentPackage, strict=False )
		if package is not None and package.ntiid:
			parts = ntiids.get_parts( package.ntiid )
			if parts and parts.provider and parts.specific:
				acl = acl + ace_allowing( authorization.role_for_providers_content( parts.provider, parts.specific ),
										  authorization.ACT_READ,
										  _DelimitedHierarchyContentPackageACLProvider )
		return acl

@interface.implementer(nti_interfaces.IACLProvider)
@component.adapter(content_interfaces.IDelimitedHierarchyContentUnit)
class _DelimitedHierarchyContentUnitACLProvider(_AbstractDelimitedHierarchyEntryACLProvider):
	"""
	For content units, we look for an acl file matching their ordinal path from
	the containing content package (e.g., first section of first chapter uses .nti_acl.1.1).
	If one does not exist, we have no opinion on the ACL and inherit it from our parent.
	"""

	_default_allow = False

	def __init__( self, context ):
		super(_DelimitedHierarchyContentUnitACLProvider,self).__init__( context )
		ordinals = []
		ordinals.append( context.ordinal )
		parent = context.__parent__
		while parent is not None and content_interfaces.IContentUnit.providedBy( parent ) and not content_interfaces.IContentPackage.providedBy( parent ):
			ordinals.append( parent.ordinal )
			parent = parent.__parent__

		ordinals.reverse()
		path = '.'.join( [str(i) for i in ordinals] )
		self._acl_sibling_entry_name = _AbstractDelimitedHierarchyEntryACLProvider._acl_sibling_entry_name + '.' + path

@component.adapter(nti_interfaces.IFriendsList)
class _FriendsListACLProvider(_CreatedACLProvider):
	"""
	Makes friends lists readable by those it contains.
	"""

	def __init__( self, obj ):
		super(_FriendsListACLProvider,self).__init__( obj )

	@Lazy
	def __acl__( self ):
		result = self._creator_acl()
		for friend in self._created:
			result.append( ace_allowing( friend.username, authorization.ACT_READ ) )
		# And finally nobody else gets jack squat
		result.append( ace_denying_all( _SectionInfoACLProvider ) )
		return result


@interface.implementer( nti_interfaces.IACLProvider )
@component.adapter(nti_interfaces.IDataserverFolder)
class _DataserverFolderACLProvider(object):

	def __init__( self, context ):
		pass

	@_LazyOnClass
	def __acl__( self ):
		# Got to be here after the components are registered
		acl = acl_from_aces(
			# Everyone has read access at the root
			ace_allowing( nti_interfaces.AUTHENTICATED_GROUP_NAME, authorization.ACT_READ, _DataserverFolderACLProvider ),
			# Global admins also get impersonation rights globally
			# TODO: We could easily site scope this, or otherwise
			ace_allowing( authorization.ROLE_ADMIN, authorization.ACT_IMPERSONATE, _DataserverFolderACLProvider )
			)
		_add_admin_moderation( acl, _DataserverFolderACLProvider )
		return acl

@interface.implementer( nti_interfaces.IACLProvider )
@component.adapter(content_interfaces.IContentPackageLibrary)
class _ContentPackageLibraryACLProvider(object):

	def __init__( self, context ):
		pass

	@_LazyOnClass
	def __acl__( self ):
		# Got to be here after the components are registered, not at the class
		return _ACL( (ace_allowing( nti_interfaces.AUTHENTICATED_GROUP_NAME, authorization.ACT_READ, _ContentPackageLibraryACLProvider ), ) )
