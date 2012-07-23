#!/usr/bin/env python
from __future__ import print_function, unicode_literals
"""
Constants and classes relating to authorisation.

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

General Principles
==================

To determine the access to some object/action pair, we follow the
*access path* to the object, from the object working towards the root
of the path. (Thus, more specific entries will override less specific
entries.) The root object should contain entries for things that apply
generally (equivalent to global capabilities.).

Persistent storage references to principals should be by their unique
identifier string (not object identity). Yet ACLs should hold
IPrincipal objects. This conversion happens through (optionally named) ZCA adapters.
Likewise, the permissions in an ACL entry should be IPermission objects,
but persistent storage should be strings; conversion is handled by registering
IPermission objects by name as utilities.

"""
import functools

import persistent
from BTrees.OOBTree import OOSet

from zope import interface
from zope import annotation
from zope import component
from zope.security.permission import Permission
import pyramid.security

import nti.dataserver.interfaces as nti_interfaces
from nti.dataserver import users


__all__ = ('ACT_CREATE', 'ACT_DELETE', 'ACT_UPDATE', 'ACT_READ',
		   'ROLE_ADMIN', 'effective_principals')

# TODO: How does zope normally present these? Side effects of import are Bad
if not '__str__' in Permission.__dict__:
	Permission.__str__ = lambda x: x.id
if not '__repr__' in Permission.__dict__:
	Permission.__repr__ = lambda x: "%s('%s','%s','%s')" % (x.__class__.__name__, x.id, x.title, x.description )
if not '__eq__' in Permission.__dict__:
	Permission.__eq__ = lambda x, y: x.id == getattr( y, 'id', Permission )

# These are also registered in configure.zcml
ACT_CREATE = Permission('nti.actions.create')
ACT_DELETE = Permission('nti.actions.delete')
ACT_UPDATE = Permission('nti.actions.update')
ACT_SEARCH = Permission('nti.actions.search')
ACT_READ   = Permission('zope.View')

# Groups that are expected to have certain rights
# in certain areas
ROLE_ADMIN = 'role:nti.admin'

import zope.deferredimport

zope.deferredimport.deprecatedFrom(
	"Prefer nti.dataserver.authentication",
	"nti.dataserver.authentication",
	"effective_principals" )

class _PersistentGroupMember(persistent.Persistent):
	"""
	Implementation of the group membership by
	storing a collection.
	"""

	interface.implements(nti_interfaces.IGroupMember)
	component.adapts(annotation.interfaces.IAttributeAnnotatable)

	def __init__( self ):
		# We store strings in this set, and adapt them to
		# IGroups during iteration.
		self._groups = OOSet()

	@property
	def groups(self):
		return (nti_interfaces.IGroup(g) for g in self._groups)

def _persistent_group_member_factory( obj ):
	return annotation.factory(_PersistentGroupMember)(obj)

# Note that principals should be comparable based solely on their ID.
# TODO: Should we enforce case-insensitivity here?
@functools.total_ordering
class _AbstractPrincipal(object):
	id = ''
	def __eq__(self,other):
		return nti_interfaces.IPrincipal.providedBy(other) \
			and self.id == getattr(other, 'id', None)
	def __lt__(self,other):
		return self.id < other.id
	def __hash__(self):
		return hash(self.id)
	def __str__(self):
		return self.id
	def __repr__(self):
		return "%s('%s')" % (self.__class__.__name__, unicode(self.id).encode('unicode_escape'))

class _StringPrincipal(_AbstractPrincipal):
	"""
	Allows any string to be an IPrincipal.
	"""
	interface.implements(nti_interfaces.IPrincipal)
	component.adapts(basestring)
	description = ''

	def __init__(self,name):
		super(_StringPrincipal,self).__init__()
		self.id = name
		self.title = name

def _system_user_factory( string ):
	assert string == nti_interfaces.SYSTEM_USER_NAME
	return nti_interfaces.system_user

class _EveryoneGroup(_StringPrincipal):
	interface.implements(nti_interfaces.IGroup)
	component.adapts(basestring)

	description = u"Everyone, authenticated or not."
	REQUIRED_NAME = nti_interfaces.EVERYONE_GROUP_NAME
	def __init__( self, string ):
		assert string == self.REQUIRED_NAME
		super(_EveryoneGroup,self).__init__( string )
		self.title = self.description

class _AuthenticatedGroup(_EveryoneGroup):

	description = u"The subset of everyone that is authenticated"
	REQUIRED_NAME = nti_interfaces.AUTHENTICATED_GROUP_NAME

def _string_principal_factory( name ):
	# Check for a named adapter first, since we are the no-name factory.
	result = component.queryAdapter( name,
									 nti_interfaces.IPrincipal,
									 name=name )
	if result is None:
		result = _StringPrincipal( name )

	return result

class _UserPrincipal(_AbstractPrincipal):
	interface.implements(nti_interfaces.IPrincipal)

	def __init__( self, user ):
		self._user = user

	@property
	def id(self):
		return self._user.username
	title = id
	description = id

# IACLProvider implementations live in authorization_acl
