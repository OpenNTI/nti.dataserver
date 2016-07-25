#!/usr/bin/env python
"""
ACL providers for the various content types.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import codecs

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.interface.interfaces import ComponentLookupError

from pyramid.security import Denied as psecDenied

from nti.common.property import alias

from nti.contentlibrary.interfaces import IContentUnit
from nti.contentlibrary.interfaces import IContentPackage
from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IContentPackageBundleLibrary
from nti.contentlibrary.interfaces import IDelimitedHierarchyContentUnit
from nti.contentlibrary.interfaces import IDelimitedHierarchyContentPackage

from nti.dataserver import authorization
from nti.dataserver import authentication

from nti.dataserver.interfaces import ACE_ACT_DENY
from nti.dataserver.interfaces import ACE_DENY_ALL
from nti.dataserver.interfaces import ACE_ALLOW_ALL
from nti.dataserver.interfaces import ACE_ACT_ALLOW
from nti.dataserver.interfaces import ALL_PERMISSIONS
from nti.dataserver.interfaces import AUTHENTICATED_GROUP_NAME

from nti.dataserver.interfaces import IACE
from nti.dataserver.interfaces import IACL
from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IEntity
from nti.dataserver.interfaces import ICreated
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IPrincipal
from nti.dataserver.interfaces import IPermission
from nti.dataserver.interfaces import IACLProvider
from nti.dataserver.interfaces import IFriendsList
from nti.dataserver.interfaces import IReadableShared
from nti.dataserver.interfaces import IEnclosedContent
from nti.dataserver.interfaces import IDataserverFolder
from nti.dataserver.interfaces import IModeledContentBody
from nti.dataserver.interfaces import IAuthorizationPolicy
from nti.dataserver.interfaces import IACLProviderCacheable
from nti.dataserver.interfaces import IShareableModeledContent
from nti.dataserver.interfaces import ICoppaUserWithoutAgreement
from nti.dataserver.interfaces import IUseNTIIDAsExternalUsername

from nti.externalization.interfaces import IExternalMappingDecorator

from nti.externalization.singleton import SingletonDecorator

from nti.ntiids import ntiids

from nti.traversal import traversal

@interface.implementer(IACE)
class _ACE(object):
	"""
	Object to hold a single ACE, permitting more descriptive code and
	prettier string output.

	These objects are persisted in their string forms.
	"""

	@classmethod
	def allowing(cls, actor=None, permission=None, provenance=None):
		"""
		:return: An :class:`.IACE` allowing the given `actor` the given `permission.`

		:param actor: The :class:`.IPrincipal` being given the permission.
			Must be an `IPrincipal` or something that can be converted to it.
		:param permission: The :class:`.IPermission` being given.
			Must be an `IPermission` or something that can be converted to it,
			or an interable sequence thereof. Also allowable is :const:`.ALL_PERMISSIONS`.
		:param provenance: A string or :class:`type` giving information about where this entry came from.
		"""
		return cls(ACE_ACT_ALLOW, actor, permission, provenance=provenance)

	@classmethod
	def denying(cls, actor=None, permission=None, provenance=None):
		"""
		:return: An :class:`.IACE` denying the given `actor` the given `permission.`

		:param actor: The :class:`.IPrincipal` being denied the permission.
			Must be an `IPrincipal` or something that can be converted to it.
		:param permission: The :class:`.IPermission` being denied.
			Must be an `IPermission` or something that can be converted to it,
			or an interable sequence thereof. Also allowable is :const:`.ALL_PERMISSIONS`.
		:param provenance: A string or :class:`type` giving information about where this entry came from.
		"""
		return cls(ACE_ACT_DENY, actor, permission, provenance=provenance)

	@classmethod
	def from_external_string(cls, string, provenance='from_string'):
		parts = string.split(':')
		__traceback_info__ = parts, string, provenance
		# It happens that we use a : to delimit parts, but that is a valid character
		# to use in a role name. We arbitrarily decide that it is not a valid character
		# to use in a permission string. This lets us take the first part as the action
		# the last part as the permission, and any parts in the middle are joined back up
		# by colons to form the actor
		assert len(parts) >= 3
		action = parts[0]
		actor = ':'.join(parts[1:-1])

		perms = parts[-1]
		if perms == 'All':
			perms = ALL_PERMISSIONS
		else:
			# trim the surrounding array chars
			perms = perms[1:-1]
			perms = [x.strip().strip("'") for x in perms.split(',')]

		return cls(action, actor, perms, provenance=provenance)

	_provenance = None

	def __init__(self, action, actor, permission, provenance=None):
		self.action = action
		assert self.action in (ACE_ACT_ALLOW, ACE_ACT_DENY)
		self.actor = (IPrincipal(actor) if not IPrincipal.providedBy(actor) else actor)
		if not hasattr(permission, '__iter__'):  # XXX breaks on py3
			permission = [permission]

		if provenance:
			self._provenance = provenance

		if permission is ALL_PERMISSIONS:
			self.permission = permission
		else:
			self.permission = [  # permissions MUST be named utilities
				(component.getUtility(IPermission, x) if not IPermission.providedBy(x) else x)
				for x in permission ]
			assert self.permission, "Must provide a permission"

	def __getstate__(self):
		return self.to_external_string()

	def __setstate__(self, state):
		other = self.from_external_string(state, provenance='from pickle')
		self.__dict__ = other.__dict__

	def to_external_string(self):
		"""
		Returns a string representing this ACE in a form that can be read
		by :meth:`from_external_string`
		"""
		return "%s:%s:%s" % (self.action,
							 self.actor.id,
							 'All' 	if self.permission is ALL_PERMISSIONS \
							 		else [str(x.id) for x in self.permission])

	def __eq__(self, other):
		# TODO: Work on this
		# This trick (reversing the order and comparing to a tuple) lets us compare
		# equal to plain tuples as used in pyramid and that sometimes sneak in
		try:
			return other == (self.action, self.actor.id, self.permission)
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		if self.permission == ALL_PERMISSIONS:
			result = (self.action, self.actor.id, ())
		else:
			result = (self.action, self.actor.id, tuple(self.permission))
		return hash(result)

	def __iter__(self):
		return iter((self.action, self.actor, self.permission))

	def __repr__(self):
		provenance = ''
		if self._provenance:
			if isinstance(self._provenance, six.string_types):
				provenance = self._provenance
			elif isinstance(self._provenance, type):
				provenance = self._provenance.__name__
			else:
				provenance = type(self._provenance).__name__
		return "<%s: %s,%s,%s%s>" % (self.__class__.__name__,
									 self.action,
									 self.actor.id,
									 getattr(self.permission, 'id', self.permission),
									 (" := " + provenance if provenance else ''))

def _ace_denying_all(provenance=None):
	return _ACE(*(ACE_DENY_ALL + (provenance,)))

def _ace_allowing_all(provenance=None):
	return _ACE(*(ACE_ALLOW_ALL + (provenance,)))

# Export these ACE functions publicly
ace_denying = _ACE.denying
ace_allowing = _ACE.allowing
ace_denying_all = _ace_denying_all
ace_allowing_all = _ace_allowing_all
ace_from_string = _ACE.from_external_string

def acl_from_file(path_or_file):
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
		provenance = getattr(path_or_file, 'name', str(path_or_file))

	return _acl_from_ace_lines(lines, provenance)

def _acl_from_ace_lines(lines, provenance):
	return _ACL([ace_from_string(x.strip(), provenance=provenance)
				  for x in lines
				  if x and x.strip() and not x.strip().startswith('#')])

def ACL(obj, default=()):
	"""
	Produce an ACL for the given `obj`. If the object already has an ACL,
	that will be returned. Otherwise, if it can be adapted into
	an :class:`.IACLProvider` it will be and that will be returned.
	If no ACL can be found, returns an empty iterable (or whatever
	the value of the `default` parameter is).
	"""
	prov = ACLProvider(obj)
	__traceback_info__ = obj, prov
	return prov.__acl__ if prov is not None else default

def ACLProvider(obj, default=None):
	"""
	Produce an ACL provider for the given `obj`. If the object already has an ACL,
	the object is its own provider. Otherwise, if it can be adapted into
	an :class:`.IACLProvider` it will be and that will be returned.
	If no ACL provider can be found, returns None (or whatever
	the value of the `default` parameter is).

	.. note::
		If the object provides :class:`.IACLProviderCacheable` (typically this will be set up
		in configuration) then the ACL derived from adapting to a provider is cached
		directly on the object. This is a side-effect.
	"""

	try:
		if obj.__acl__ is not None:
			return obj
	except AttributeError:
		try:
			result = IACLProvider(obj)
			if IACLProviderCacheable.providedBy(obj):
				obj.__acl__ = result.__acl__
				result = obj
			return result
		except TypeError:
			return default

def has_permission(permission, context, username, **kwargs):
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
			# XXX: JAM: This is probably a bug. Although it lets us work
			# with a pure stock pyramid authorization policy, if the policy
			# is actually the one supplied by nti.appserver.pyramid_authorization
			# that automatically fills in the ACLs, then we are potentially
			# losing the tree.
			# A workaround, where this is a problem, is to be sure the ACL provider
			# object returns the parent of its context.
			to_check = IACLProvider(context)
		except TypeError:
			return psecDenied("No ACL found")
	else:
		to_check = context

	policy = component.queryUtility(IAuthorizationPolicy)
	if not policy:
		return psecDenied("No IAuthorizationPolicy installed")

	principals = kwargs.get('principals', None)
	if not principals:
		principals = authentication.effective_principals(username, **kwargs)
	result = policy.permits(to_check, principals, permission)
	return result

def is_writable(context, username, **kwargs):
	"""
	Is the ``context`` object writable by the ``username``? The ``context`` object should
	generally not be an already-externalized object.

	A shortcut to :func:``has_permission``; see its docs for details.
	"""
	return has_permission(authorization.ACT_UPDATE, context, username, **kwargs)

import functools

from ZODB.POSException import POSError

@component.adapter(object)
@interface.implementer(IExternalMappingDecorator)
class ACLDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalMapping(self, orig, result):
		try:
			if hasattr(orig, '__acl__') and result.__acl__ is not None:
				return
			# we'd like to make the ACL available. Pyramid
			# supports either a callable or the flattened list;
			# defer it until/if we need it by using a callable because
			# computing it can be expensive if the cache is cold.
			result.__acl__ = functools.partial(ACL, orig)
		except POSError:
			logger.warn("Failed to get ACL on POSError")
			result.__acl__ = ()

@interface.implementer(IACL)
class _ACL(list):

	def __add__(self, other):
		"We allow concatenating single ACE objects to an ACL to produce a new ACL"
		if isinstance(other, _ACE):
			result = _ACL(self)
			result.append(other)
			return result
		return super(_ACL, self).__add__(other)

	def write_to_file(self, path_or_file):
		"""
		Given a path to a writable file or a file-like object (having the `write` method),
		writes each entry in this ACL to the file.
		:return: None
		"""
		def _write(f):
			for x in self:
				f.write(x.to_external_string())
				f.write('\n')

		if isinstance(path_or_file, six.string_types):
			with codecs.open(path_or_file, 'w', encoding='utf-8') as f:
				_write(f)
		else:
			_write(path_or_file)

def acl_from_aces(*args):
	"""
	Create an ACL from ACEs.
	Can either provide a list of ACEs, or var-args that are individual ACEs.
	"""
	if len(args) == 1:
		if isinstance(args[0], _ACE):
			return _ACL((args[0],))
		return _ACL(args[0])
	return _ACL(args)

from nti.common.property import LazyOnClass as _LazyOnClass

def _add_admin_moderation(acl, provenance):
	# admin
	for perm in (authorization.ACT_MODERATE,
				 authorization.ACT_NTI_ADMIN,
				 authorization.ACT_CONTENT_EDIT):
		acl.append(ace_allowing(authorization.ROLE_ADMIN, perm, provenance))
	# moderators
	acl.append(ace_allowing(authorization.ROLE_MODERATOR,
							authorization.ACT_MODERATE,
							provenance))
	# editors
	acl.append(ace_allowing(authorization.ROLE_CONTENT_EDITOR,
							authorization.ACT_CONTENT_EDIT,
							provenance))

@interface.implementer(IACLProvider)
@component.adapter(IEntity)
class _EntityACLProvider(object):
	"""
	ACL provider for class:`.interfaces.IEntity` objects. The
	entity itself is allowed all permissions.
	"""
	# TODO: Extend this for other subclasses such as communities?
	# Define 'roles' and make Users members of roles that represent
	# their community

	_DENY_ALL = True

	def __init__(self, entity):
		self._entity = entity

	def _viewers(self):
		return (AUTHENTICATED_GROUP_NAME,)

	def _do_get_deny_all(self):
		return self._DENY_ALL

	@Lazy
	def __acl__(self):
		"""
		The ACL for the entity.
		"""
		acl = _ACL([ace_allowing(self._entity.username, ALL_PERMISSIONS, self)])
		for viewer in self._viewers():
			acl.append(ace_allowing(viewer, authorization.ACT_READ, self))
		_add_admin_moderation(acl, self)
		if self._do_get_deny_all():
			# Everyone else can do nothing
			acl.append(_ace_denying_all(_EntityACLProvider))
		return acl

@interface.implementer(IACLProvider)
@component.adapter(ICommunity)
class _CommunityACLProvider(_EntityACLProvider):
	"""
	ACL provider for class:`.interfaces.ICommunity` objects. The
	entity itself is allowed all permissions.
	"""

	def _viewers(self):
		return (AUTHENTICATED_GROUP_NAME,) if self._entity.public else ()

	@Lazy
	def __acl__(self):
		"""
		The ACL for the community.
		"""
		if IUseNTIIDAsExternalUsername.providedBy(self._entity):
			username = self._entity.NTIID
		else:
			username = self._entity.username
		acl = _ACL([ace_allowing(username, ALL_PERMISSIONS, self)])
		acl.append(ace_allowing(authorization.ROLE_ADMIN, ALL_PERMISSIONS, self))
		acl.append(ace_allowing(authorization.ROLE_MODERATOR, authorization.ACT_MODERATE, self))
		for viewer in self._viewers():
			acl.append(ace_allowing(viewer, authorization.ACT_READ, self))
		if self._do_get_deny_all():
			acl.append(_ace_denying_all(_CommunityACLProvider))
		return acl

@component.adapter(IUser)
class _UserACLProvider(_EntityACLProvider):
	"""
	ACL Provider for :class:`.interfaces.IUser`.
	"""

	def _viewers(self):
		# intersecting community members have viewing rights
		# this is a private function while in flux
		return authentication._dynamic_memberships_that_participate_in_security(self._entity)

@component.adapter(ICoppaUserWithoutAgreement)
class _CoppaUserWithoutAgreementACLProvider(_UserACLProvider):
	"""
	ACL Provider for Koppa Kids that limits all access to them.
	"""

	def _viewers(self):
		return ()  # nobody!

@interface.implementer(IACLProvider)
@component.adapter(ICreated)
class _CreatedACLProvider(object):
	"""
	ACL provider for class:`ICreated` objects.
	The creator of an object is allowed all permissions.

	.. py:attribute:: _DENY_ALL

		Subclasses can set this to ``True`` (default is ``False``) to force explicitly
		denying all access to everyone not otherwise listed as having access.

	"""

	def __init__(self, created):
		self._created = created

	context = alias('_created')

	_REQUIRE_CREATOR = False
	_PERMS_FOR_CREATOR = (ALL_PERMISSIONS,)
	_DENY_ALL = True

	def _do_get_deny_all(self):
		"""
		If the context object has the special attribute __acl_deny_all__,
		that takes priority over our value for _DENY_ALL
		"""
		return getattr(self._created, '__acl_deny_all__', self._DENY_ALL)

	def _do_get_perms_for_creator(self):
		return self._PERMS_FOR_CREATOR

	def _creator_acl(self):
		"""
		Creates the ACL for just the creator; subclasses may call.

		:return: A fresh, mutable list containing at most one :class:`_ACE` for
				the creator (if there is a creator).
		"""
		result = _ACL([ace_allowing(self._created.creator, x, self) for x in self._do_get_perms_for_creator()]
					  if getattr(self._created, 'creator', None)  # They don't all comply with the interface
					  else [])
		if self._REQUIRE_CREATOR and len(result) != 1:
			raise ValueError("Unable to get creator", self._created)
		return result

	def _extend_acl_before_deny(self, acl):
		"""
		Called after the creator and sharing target acls have been added, and after optional extensions, but
		before the deny-everyone is added (and only if it will be added). You can add additional options here.
		"""
		return

	def _handle_deny_all(self, acl):
		if self._do_get_deny_all():
			self._extend_acl_before_deny(acl)
			acl.append(_ace_denying_all(type(self)))
		return acl

	@Lazy
	def __acl__(self):
		"""
		The ACL for the creator.

		:return: A fresh, mutable list containing at exactly two :class:`_ACE` for
				the creator (if there is a creator), and one denying all rights to everyone else.
		"""
		acl = self._creator_acl()
		return self._handle_deny_all(acl)

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

	_PERMS_FOR_SHARING_TARGETS = (authorization.ACT_READ,)
	_DENY_ALL = False  # Override superclass

	def _get_sharing_target_names(self):
		"""
		Subclasses implement to return an iterable over names (or principals) that should have
		the access given in :data:`_PERMS_FOR_SHARING_TARGETS`. Each element of the returned
		sequence will be adapted to an :class:`nti.dataserver.interfaces.IPrincipal`.
		"""
		raise NotImplementedError()  # pragma: no cover

	def __do_get_sharing_target_names(self):
		try:
			return self._get_sharing_target_names()
		except POSError:
			logger.warn("POSError getting sharing target names.")
			return ()

	def _extend_acl_after_creator_and_sharing(self, acl):
		"""
		Called after the creator and sharing target acls have been added to add
		optional extensions. A deny-all may be added following this.
		"""
		return

	def _extend_with_admin_privs(self, acl, provenance=None):
		"""
		Subclasses need to call this if admins should have full permissions,
		from `_extend_acl_after_creator_and_sharing`.
		"""
		provenance = provenance or self
		_add_admin_moderation(acl, provenance)
		acl.append(ace_allowing(authorization.ROLE_MODERATOR, authorization.ACT_READ, provenance))
		acl.append(ace_allowing(authorization.ROLE_ADMIN, ALL_PERMISSIONS, provenance))

	def _do_get_perms_for_sharing_targets(self):
		return self._PERMS_FOR_SHARING_TARGETS

	def _extend_for_sharing_target(self, target, acl):
		for perm in self._do_get_perms_for_sharing_targets():
			acl.append(ace_allowing(target, perm, type(self)))

	@Lazy
	def __acl__(self):
		"""
		The ACL for this object. If this class sets :attr:`_DENY_ALL` to ``True`` then everyone
		not explicitly listed is denied any access.
		"""
		result = self._creator_acl()
		for name in self.__do_get_sharing_target_names():
			__traceback_info__ = name
			self._extend_for_sharing_target(name, result)
		self._extend_acl_after_creator_and_sharing(result)
		return self._handle_deny_all(result)

@component.adapter(IShareableModeledContent)
class _ShareableModeledContentACLProvider(AbstractCreatedAndSharedACLProvider):
	"""
	Extends the ACL for :class:`nti.dataserver.interfaces.ICreated` objects to things that
	are shared.

	Those things that are shared can be viewed (:data:`authorization.ACT_READ`) by those they are
	shared with. The ACL is composed of the sharingTargets. Members of these groups
	must have these groups/communities in their effective principals.

	This is modified: If this object is the child of another :class:`.IReadableShared`
	or :class:`IModeledContentBody`, e.g., a Canvas inside a Note, then the ACL
	is skipped and just inherited from the parent (so traversal must be appropriate
	and respected in ACL checks). This prevents problems when denying all access.

	.. note:: Even in this case, we still give administrators/moderators access
		to the nested object. This is something of a hack: we don't really want them
		to have full, indiscriminate access to the parent object because that breaks
		certain assumptions about sharing (some objects are visible when we don't expect
		them to be because they weren't shared with you), but we do need access to the inner
		objects, primarily Canvas objects and the image files they contain.

		This strategy would fail if canvas objects were ever used top-level.
	"""

	_DENY_ALL = True

	def _get_sharing_target_names(self):
		return self.context.sharingTargetNames

	@Lazy
	def __acl__(self):
		# Inherit if we are nested. See class comment. NOTE: We are just checking the direct parent,
		# not the entire traversal chain; checking to see if anything we are within is IReadableShared
		# might pull in the wrong permissions, depending on how the nesting goes (?)
		parent = getattr( self.context, '__parent__', None )
		if 		IReadableShared.providedBy( parent ) \
			or  IModeledContentBody.providedBy( parent ):
			result = _ACL()
			self._extend_with_admin_privs(result, 'Nested _ShareableModeledContentACLProvider')
			return result
		return super(_ShareableModeledContentACLProvider, self).__acl__

@component.adapter(IEnclosedContent)
class _EnclosedContentACLProvider(_CreatedACLProvider):
	"""
	The ACL for enclosed content depends on a few things, most notably
	whether the content it is enclosing itself has an ACL.
	"""

	def __init__(self, obj):
		super(_EnclosedContentACLProvider, self).__init__(obj)

	@Lazy
	def __acl__(self):
		# Give the creator full rights.
		result = self._creator_acl()
		# Add to this any ACL we can determine for the enclosed
		# content
		result.extend(ACL(self._created.data))
		return result

@interface.implementer(IACLProvider)
@component.adapter(IContentUnit)
class _TestingLibraryTOCEntryACLProvider(object):
	"""
	Allows all authenticated users access to library entries.
	This class is for testing only, never for use in a production scenario.
	"""

	def __init__(self, context):
		self.context = context

	@property
	def __parent__(self):
		return self.context.__parent__

	@Lazy
	def __acl__(self):
		return (ace_allowing(AUTHENTICATED_GROUP_NAME,
							 ALL_PERMISSIONS,
							 _TestingLibraryTOCEntryACLProvider),)

# TODO: This could be (and was) registered for a simple IDelimitedHierarchyEntry.
# There is none of that separate from the contentpackage/unit though, so it shouldn't
# be needed in that capacity.
class _AbstractDelimitedHierarchyEntryACLProvider(object):
	"""
	Checks a hierarchy entry for the existence of a file (typically .'.nti_acl'), and if present,
	reads an ACL from it.

	Otherwise, the ACL allows all authenticated users access.
	"""

	def __init__(self, context):
		self.context = context

	_acl_sibling_entry_name = '.nti_acl'
	# : If defined by a subclass, this will be checked
	# : when `_acl_sibling_entry_name` does not exist.
	_acl_sibling_fallback_name = None
	_default_allow = True
	_add_default_deny_to_acl_from_file = False

	__parent__ = property(lambda self: self.context.__parent__)

	@Lazy
	def __acl__(self):
		provenance = self._acl_sibling_entry_name
		acl_string = self.context.read_contents_of_sibling_entry(self._acl_sibling_entry_name)
		if acl_string is None and self._acl_sibling_fallback_name is not None:
			provenance = self._acl_sibling_fallback_name
			acl_string = self.context.read_contents_of_sibling_entry(self._acl_sibling_fallback_name)
		if acl_string is not None:
			try:
				__acl__ = self._acl_from_string(self.context, acl_string, provenance)
				# Empty files (those that do exist but feature no valid ACL lines)
				# are considered a mistake, an overlooked accident. In the interest of trying
				# to be secure by default and not allow oversights through, call them out.
				# This results in default-deny
				if not __acl__:
					raise ValueError("ACL file had no valid contents.")
				if self._add_default_deny_to_acl_from_file:
					__acl__.append(_ace_denying_all('Default Deny After File ACL'))
			except (ValueError, AssertionError, TypeError, ComponentLookupError):
				logger.exception("Failed to read acl from %s/%s; denying all access.",
								 self.context, self._acl_sibling_entry_name)
				__acl__ = _ACL((_ace_denying_all('Default Deny Due to Parsing Error'),))
		elif self._default_allow:
			__acl__ = _ACL((ace_allowing(AUTHENTICATED_GROUP_NAME,
										 ALL_PERMISSIONS,
										 _AbstractDelimitedHierarchyEntryACLProvider),))
		else:
			__acl__ = ()  # Inherit from parent

		return __acl__

	def _acl_from_string(self, context, acl_string, provenance=None):
		return _acl_from_ace_lines(acl_string.splitlines(), provenance or context)

def _supplement_acl_with_content_role(self, context, acl):
	"""
	Add read-access to a pseudo-group
	based on the (lowercased) NTIID of the closest containing content package.

	It is important to do this both for the root and sublevels of the tree that allow
	ACLs to be specified in files, because we may be putting a default Deny entry
	there. (The default deny at the sub files is needed to be sure
	that we can properly mix granting and denying access and forces acl files
	to be very specific.)
	"""

	package = traversal.find_interface(context, IContentPackage, strict=False)
	if package is not None and package.ntiid:
		parts = ntiids.get_parts(package.ntiid)
		if parts and parts.provider and parts.specific:
			acl = acl + ace_allowing(authorization.role_for_providers_content(parts.provider, parts.specific),
									 authorization.ACT_READ,
									 self)
	return acl

@interface.implementer(IACLProvider)
@component.adapter(IDelimitedHierarchyContentPackage)
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

	@Lazy
	def __acl__(self):
		acl = super(_DelimitedHierarchyContentPackageACLProvider, self).__acl__
		# Make sure our content admin comes first.
		admin_ace = ace_allowing(authorization.ROLE_CONTENT_ADMIN,
								 authorization.ACT_READ,
						 		 self)
		acl.insert(0, admin_ace)
		return acl

	def _acl_from_string(self, context, acl_string, provenance=None):
		acl = super(_DelimitedHierarchyContentPackageACLProvider, self)._acl_from_string(context, acl_string, provenance=provenance)
		acl = _supplement_acl_with_content_role(self, context, acl)
		return acl

@interface.implementer(IACLProvider)
@component.adapter(IDelimitedHierarchyContentUnit)
class _DelimitedHierarchyContentUnitACLProvider(_AbstractDelimitedHierarchyEntryACLProvider):
	"""
	For content units, we look for an acl file matching their ordinal
	path from the containing content package (e.g., first section of
	first chapter uses ``.nti_acl.1.1``). If such a file does not exist,
	we have no opinion on the ACL and inherit it from our parent. If
	such a file does exist but is empty, it is treated as if it denied
	all access; this is considered a mistake.

	As a special case, for those items that are directly beneath a
	content package (e.g. chapters), if there is no specific file, we
	will use a file named ``.nti_acl.default``. This permits easily
	granting access to the whole content package (through
	``.nti_acl``), letting it show up in libraries, etc, generally
	denying access to children (through ``.nti_acl.default``), but
	providing access to certain subunits (through the ordinal files).
	In this case, we will also place a default global denial as the
	last entry in the ACL, forcing permissioning to be at this level
	(e.g., the parent ACL from the content package is thus effectively
	NOT inherited.)
	"""

	_default_allow = False

	def __init__(self, context):
		super(_DelimitedHierarchyContentUnitACLProvider, self).__init__(context)
		ordinals = []
		ordinals.append(context.ordinal)
		parent = context.__parent__
		while (parent is not None and
				IContentUnit.providedBy(parent) and
			  	not IContentPackage.providedBy(parent)):
			ordinals.append(parent.ordinal)
			parent = parent.__parent__

		ordinals.reverse()
		path = '.'.join([str(i) for i in ordinals])
		self._acl_sibling_entry_name = _AbstractDelimitedHierarchyEntryACLProvider._acl_sibling_entry_name + '.' + path

		if len(ordinals) == 1:  # a "chapter"; we don't do this at every level for efficiency (TODO: For best caching, we need to read this off the ContentPackage)
			self._acl_sibling_fallback_name = _AbstractDelimitedHierarchyEntryACLProvider._acl_sibling_entry_name + '.default'
			self._add_default_deny_to_acl_from_file = True

	def _acl_from_string(self, context, acl_string, provenance=None):
		acl = super(_DelimitedHierarchyContentUnitACLProvider, self)._acl_from_string(context, acl_string, provenance=provenance)
		return 	_supplement_acl_with_content_role(self, context, acl) \
				if self._acl_sibling_fallback_name else acl

@component.adapter(IFriendsList)
class _FriendsListACLProvider(_CreatedACLProvider):
	"""
	Makes friends lists readable by those it contains.
	"""

	def __init__(self, obj):
		super(_FriendsListACLProvider, self).__init__(obj)

	@Lazy
	def __acl__(self):
		result = self._creator_acl()
		for friend in self._created:
			result.append(ace_allowing(friend.username, authorization.ACT_READ))
		# And finally nobody else gets jack squat
		result.append(ace_denying_all(_FriendsListACLProvider))
		return result

@interface.implementer(IACLProvider)
@component.adapter(IDataserverFolder)
class _DataserverFolderACLProvider(object):

	def __init__(self, context):
		pass

	@_LazyOnClass
	def __acl__(self):
		# Got to be here after the components are registered
		acl = acl_from_aces(
			# Everyone logged in has read and search access at the root
			ace_allowing(AUTHENTICATED_GROUP_NAME,
						 authorization.ACT_READ,
						 _DataserverFolderACLProvider),
			ace_allowing(AUTHENTICATED_GROUP_NAME,
						 authorization.ACT_SEARCH,
						 _DataserverFolderACLProvider),
			# Global admins also get impersonation rights globally
			# TODO: We could easily site scope this, or otherwise
			ace_allowing(authorization.ROLE_ADMIN,
						 authorization.ACT_IMPERSONATE,
						 _DataserverFolderACLProvider),
			# Global admins also get library sync rights globally
			ace_allowing(authorization.ROLE_ADMIN,
						 authorization.ACT_SYNC_LIBRARY,
						 _DataserverFolderACLProvider),
			# Global admins also get content edit rights globally
			ace_allowing(authorization.ROLE_ADMIN,
						 authorization.ACT_CONTENT_EDIT,
						 _DataserverFolderACLProvider),
			# Global content admins also get edit rights
			ace_allowing(authorization.ROLE_CONTENT_ADMIN,
						 authorization.ACT_CONTENT_EDIT,
						 _DataserverFolderACLProvider),
			# Global content admins also sync lib
			ace_allowing(authorization.ROLE_CONTENT_ADMIN,
						 authorization.ACT_SYNC_LIBRARY,
						 _DataserverFolderACLProvider)
		)
		_add_admin_moderation(acl, _DataserverFolderACLProvider)
		return acl

# Content/bundle library.
# TODO: These should move up to nti.app.contentlibrary.

@interface.implementer(IACLProvider)
@component.adapter(IContentPackageLibrary)
class _ContentPackageLibraryACLProvider(object):

	def __init__(self, context):
		pass

	@_LazyOnClass
	def __acl__(self):
		# Got to be here after the components are registered, not at the class
		return _ACL((ace_allowing(AUTHENTICATED_GROUP_NAME,
								  authorization.ACT_READ,
								  _ContentPackageLibraryACLProvider),))

@interface.implementer(IACLProvider)
@component.adapter(IContentPackageBundleLibrary)
class _ContentPackageBundleLibraryACLProvider(object):

	def __init__(self, context):
		pass

	@_LazyOnClass
	def __acl__(self):
		# Got to be here after the components are registered, not at the class
		return _ACL((ace_allowing(AUTHENTICATED_GROUP_NAME,
								  authorization.ACT_READ,
								  _ContentPackageLibraryACLProvider),))
