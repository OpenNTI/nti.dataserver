#!/usr/bin/env python2.7
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
import persistent
from BTrees.OOBTree import OOSet

from zope import interface
from zope import annotation
from zope import component

import nti.dataserver.interfaces as nti_interfaces
from zope.security.permission import Permission

# TODO: How does zope normally present these? Side effects of import are bad
if not '__str__' in Permission.__dict__:
	Permission.__str__ = lambda x: x.id
if not '__repr__' in Permission.__dict__:
	Permission.__repr__ = lambda x: "%s('%s','%s','%s')" %(x.__class__.__name__, x.id, x.title, x.description )
if not '__eq__' in Permission.__dict__:
	Permission.__eq__ = lambda x, y: x.id == getattr( y, 'id', x )


ACT_CREATE = Permission('nti.actions.create')
ACT_DELETE = Permission('nti.actions.delete')
ACT_UPDATE = Permission('nti.actions.update')
ACT_READ   = Permission('nti.actions.read')

# Groups that are expected to have certain rights
# in certain areas
ROLE_ADMIN = 'role:nti.admin'

class PersistentGroupMember(persistent.Persistent):
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
	return annotation.factory(PersistentGroupMember)(obj)

# TODO: Adapter from strings to IPrincipal. Register one of these special
# by name for system_user
# TODO: Likewise for IGroup.
# TODO: Adapter from nti.ds.users.User to IPrincipal.

# TODO: IACLProvider implementation
