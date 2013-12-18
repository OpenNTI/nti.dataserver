#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Constants and classes relating to authorisation (principals, groups,
and group memberships).

Comparison to libACL
====================

The previous system, libACL, made a distinction between three axis of
security:

*Authentication*
	Are you who you say you are?

*Authorization*
	Can you take the action you are proposing?

*Access Control*
	If you are who you say you are, and you can generally perform the
	action, can you perform it to this specific bit of data?

Authorization was provided by a system of *capabilities* would could
be assigned to individual users, groups, or roles. A user could belong
to any number of groups and roles. These capabilities were effectively
global in nature and were open-ended.

Access control was specific to individual bits of data and was
implemented by providing each object with an ACL, which listed groups
or principals and their assigned access rights. These rights were
fixed to a small set.

In practice, ACLs and capabilities were rarely combined. Either a
capability was required, or an object was protected with an ACL.

Noting that fact we simplify things here by combining authorization
with access control and calling the result simply authorization.

.. note::
   Higher levels may group together collections of permissions or access to
   defined features and call those "capabilities."

General Principles
==================

To determine the access to some object/action pair, we follow the
*access path* to the object, from the object working towards the root
of the path. (Thus, more specific entries will override less specific
entries.) The root object should contain entries for things that apply
generally (equivalent to global capabilities.).

Persistent storage references to principals should be by their unique
identifier string (not object identity). Yet ACLs should hold
``IPrincipal`` objects. This conversion happens through (optionally named)
ZCA adapters. Likewise, the permissions in an ACL entry should be
``IPermission`` objects, but persistent storage should be strings;
conversion is handled by registering ``IPermission`` objects by name as
utilities.

Namespaces
==========

Principals, groups, and roles all share a flat namespace. Principals
(and groups and communities) do not have a prefix. Roles have a prefix ending in ``role:``;
sub-types of roles may have a prefix to that, such as ``content-role:``.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import functools

import persistent
from BTrees.OOBTree import OOSet

from zope import interface
from zope import component
from zope import annotation
from zope.container import contained
from zope.cachedescriptors.property import Lazy

from zope.annotation.interfaces import IAnnotations

from zope.security.permission import Permission

import nti.dataserver.interfaces as nti_interfaces

# TODO: How does zope normally present these? Side effects of import are Bad
if not '__str__' in Permission.__dict__:
	Permission.__str__ = lambda x: x.id
if not '__repr__' in Permission.__dict__:
	Permission.__repr__ = lambda x: "%s('%s','%s','%s')" % (x.__class__.__name__, x.id, x.title, x.description )
if not '__eq__' in Permission.__dict__:
	Permission.__eq__ = lambda x, y: x.id == getattr( y, 'id', Permission )

# These are also registered in configure.zcml
ACT_CREATE   = Permission('nti.actions.create')
ACT_DELETE   = Permission('nti.actions.delete')
ACT_UPDATE   = Permission('nti.actions.update')
ACT_SEARCH   = Permission('nti.actions.search')
ACT_MODERATE = Permission('nti.actions.moderate')
ACT_COPPA_ADMIN = Permission('nti.actions.coppa_admin')
ACT_IMPERSONATE = Permission('nti.actions.impersonate')
ACT_READ     = Permission('zope.View')

@interface.implementer(nti_interfaces.IMutableGroupMember)
@component.adapter(annotation.interfaces.IAttributeAnnotatable)
class _PersistentGroupMember(persistent.Persistent,
							 contained.Contained): # (recall annotations should be IContained)
	"""
	Implementation of the group membership by
	storing a collection.
	"""

	GROUP_FACTORY = nti_interfaces.IGroup

	def __init__( self ):
		pass

	@Lazy
	def _groups(self):
		"""We store strings in this set, and adapt them to
		IGroups during iteration."""

		groups = OOSet()
		self._p_changed = True
		if self._p_jar:
			self._p_jar.add( groups )
		return groups

	@property
	def groups(self):
		if not self.hasGroups():
			return ()

		return (self.GROUP_FACTORY(g) for g in self._groups)

	def setGroups( self, value ):
		# take either strings or IGroup objects
		groups = {getattr(x,'id', x) for x in value}
		self._groups.clear()
		self._groups.update( groups )

	def hasGroups( self ):
		return '_groups' in self.__dict__ and len(self._groups)

# This factory is registered for the default annotation
_persistent_group_member_factory = annotation.factory(_PersistentGroupMember)

class _PersistentRoleMember(_PersistentGroupMember):
	GROUP_FACTORY = nti_interfaces.IRole

def _make_group_member_factory( group_type, factory=_PersistentGroupMember ):
	"""
	Create and return a factory suitable for use adapting to
	:class:`nti.dataserver.interfaces.IMutableGroupMember` for things
	that can be annotated; the objects produced by the factory are
	themselves persistent.

	:param str group_type: A string naming the type of groups this membership
		will record. This is used as part of the annotation key; this factory
		should be registered with the same name as the ``group_type``
	"""
	key = factory.__module__ + '.' + factory.__name__ + ':' + group_type
	return annotation.factory( factory, key )

# Note that principals should be comparable based solely on their ID.
# TODO: Should we enforce case-insensitivity here?
@functools.total_ordering
class _AbstractPrincipal(object):
	"""
	Root for all actual :class:`nti_interfaces.IPrincipal` implementations.
	"""
	id = ''
	def __eq__(self,other):
		try:
			return self is other or self.id == other.id
		except AttributeError:
			return NotImplemented

	def __lt__(self,other):
		return self.id < other.id
	def __hash__(self):
		return hash(self.id)
	def __str__(self):
		return self.id
	def __repr__(self):
		return "%s('%s')" % (self.__class__.__name__, unicode(self.id).encode('unicode_escape'))

@interface.implementer(nti_interfaces.IPrincipal)
@component.adapter(basestring)
class _StringPrincipal(_AbstractPrincipal):
	"""
	Allows any string to be an IPrincipal.
	"""
	description = ''

	def __init__(self,name):
		super(_StringPrincipal,self).__init__()
		self.id = name
		self.title = name

def _system_user_factory( string ):
	assert string in (nti_interfaces.SYSTEM_USER_NAME, nti_interfaces.SYSTEM_USER_ID)
	return nti_interfaces.system_user

@interface.implementer(nti_interfaces.IGroup)
@component.adapter(basestring)
class _StringGroup(_StringPrincipal):
	"""
	Allows any string to be an IGroup.
	"""

@interface.implementer(nti_interfaces.IRole)
class _StringRole(_StringGroup):
	pass

ROLE_PREFIX = 'role:'
CONTENT_ROLE_PREFIX = 'content-role:'

_content_role_member_factory = _make_group_member_factory( CONTENT_ROLE_PREFIX, _PersistentRoleMember )

def role_for_providers_content( provider, local_part ):
	"""
	Create an IRole for access to content provided by the given ``provider``
	and having the local (specific) part of an NTIID matching ``local_part``
	"""
	return nti_interfaces.IRole( CONTENT_ROLE_PREFIX + provider.lower() + ':' + local_part.lower())

#: Name of the super-user group that is expected to have full rights
#: in certain areas
ROLE_ADMIN_NAME = ROLE_PREFIX + 'nti.admin'
ROLE_ADMIN = _StringRole( ROLE_ADMIN_NAME )

#: Name of the high-permission group that is expected to have certain
#: moderation-like rights in certain areas
ROLE_MODERATOR_NAME = ROLE_PREFIX + 'nti.moderator'
ROLE_MODERATOR = _StringRole( ROLE_MODERATOR_NAME )

# TODO: Everyone and Authenticated can go away
# through the use of the principal registry
class _EveryoneGroup(_StringGroup):
	"Everyone, authenticated or not."

	REQUIRED_NAME = nti_interfaces.EVERYONE_GROUP_NAME
	def __init__( self, string ):
		assert string == self.REQUIRED_NAME
		super(_EveryoneGroup,self).__init__( string )
		self.title = self.description

	def __eq__(self,other):
		"""
		We also allow ourself to be equal to the string version
		of our id. This is because of the unauthenticated case:
		in that case, our code that adds this object to
		the list of principal identities is never called,
		leaving ACLs that are defined with this IPrincipal
		to fail.
		"""
		result = _StringGroup.__eq__(self,other)
		if result is NotImplemented and isinstance(other,basestring):
			result = self.id == other
		return result


_EveryoneGroup.description = _EveryoneGroup.__doc__

class _AuthenticatedGroup(_EveryoneGroup):
	"The subset of everyone that is authenticated"

	REQUIRED_NAME = nti_interfaces.AUTHENTICATED_GROUP_NAME

_AuthenticatedGroup.description = _AuthenticatedGroup.__doc__

def _string_principal_factory( name ):
	if not name:
		return None

	# Check for a named adapter first, since we are the no-name factory.
	# Note that this might return an IGroup
	result = component.queryAdapter( name,
									 nti_interfaces.IPrincipal,
									 name=name )
	if result is None:
		result = _StringPrincipal( name )

	return result

def _string_group_factory( name ):
	if not name:
		return None

	# Try the named factory
	result = component.queryAdapter( name,
									 nti_interfaces.IGroup,
									 name=name )
	if result is None:
		# Try the principal factory, see if something is registered
		result = component.queryAdapter( name,
										 nti_interfaces.IPrincipal,
										 name=name )

	if nti_interfaces.IGroup.providedBy( result ):
		return result
	return _StringGroup(name)


def _string_role_factory( name ):
	if not name:
		return None

	# Try the named factory
	result = component.queryAdapter( name,
									 nti_interfaces.IRole,
									 name=name )
	if result is None:
		# Try the principal factory, see if something is registered
		# that turns out to be a role
		result = component.queryAdapter( name,
										 nti_interfaces.IPrincipal,
										 name=name )

	if nti_interfaces.IRole.providedBy( result ):
		return result
	return _StringRole(name)

@interface.implementer(nti_interfaces.IPrincipal)
@component.adapter(nti_interfaces.IUser)
class _UserPrincipal(_AbstractPrincipal):
	"""
	Adapter from an :class:`nti_interfaces.IUser` to an :class:`nti_interfaces.IPrincipal`.
	"""

	def __init__( self, user ):
		self.context = user

	@property
	def id(self):
		return self.context.username
	title = id
	description = id

@interface.implementer(nti_interfaces.IGroupAwarePrincipal)
@component.adapter(nti_interfaces.IUser)
class _UserGroupAwarePrincipal(_UserPrincipal):

	@property
	def groups(self):
		return nti_interfaces.IMutableGroupMember(self.context).groups

# Reverses that back to annotations
def _UserGroupAwarePrincipalAnnotations( _ugaware_principal, *args ): # optional multi-adapt
	return IAnnotations(_ugaware_principal.context)

# Reverses that back to externalization
from nti.externalization.interfaces import IExternalObject
def _UserGroupAwarePrincipalExternalObject( _ugaware_principal ):
	return IExternalObject(_ugaware_principal.context)

@interface.implementer(nti_interfaces.IPrincipal)
class _CommunityGroup(_UserPrincipal): # IGroup extends IPrincipal
	pass

@interface.implementer(nti_interfaces.IPrincipal)
@component.adapter(nti_interfaces.IDynamicSharingTargetFriendsList)
class _DFLPrincipal(_UserPrincipal):
	pass
_DFLGroup = _DFLPrincipal

# IACLProvider implementations live in authorization_acl
