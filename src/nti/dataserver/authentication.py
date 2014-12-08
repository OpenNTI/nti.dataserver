#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes and functions related to authentication.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import contextlib

from zope import component
from zope import interface

from nti.dataserver import interfaces as nti_interfaces

def _dynamic_memberships_that_participate_in_security( user, as_principals=True ):
	# Add principals for all the communities that the user is in
	# These are valid ACL targets because they are in the same namespace
	# as users (so no need to prefix with community_ or something like that)
	for community in getattr( user, 'dynamic_memberships', ()): # Mostly tests pass in a non-User user_factory
		# Make sure it's a valid community
		if 	nti_interfaces.IDynamicSharingTargetFriendsList.providedBy(community) or \
			(nti_interfaces.ICommunity.providedBy(community) and \
			 not nti_interfaces.IUnscopedGlobalCommunity.providedBy(community)):
			yield nti_interfaces.IPrincipal(community) if as_principals else community
	# XXX: This is out of sync with the sharing target's xxx_intids_of_memberships_and_self
	# which is used as an ACL optimization

def _user_factory( username ):
	# To avoid circular imports (sharing imports us, users imports us, we import users). sigh.
	from nti.dataserver.users import User
	return User.get_user( username )

# We will cache effective principals on the current request
# XXX TODO: This isn't very clean and is a poor
# separation of concerns
from pyramid.threadlocal import get_current_request

def effective_principals( username,
						  registry=component,
						  authenticated=True,
						  user_factory=_user_factory,
						  request=None ):
	"""
	Find and return the principals for the given username. This will include
	the username itself (obviously), plus a principal for Everyone, plus
	any groups the user is in (as found with :class:`~nti.dataserver.interfaces.IGroupMember`)

	:param username: Either a string giving a username to be looked up,
		or a user object having the ``username`` attribute.
	:param registry: The component registry to query. Defaults to the global
		registry.
	:keyword bool authenticated: If True (the default) assume this user is properly
		authenticated, and add the pseudo-group for authenticated people as a
		principal.
	:return: An iterable (set) of :class:`nti.dataserver.interfaces.IPrincipal` objects.
	"""

	if not username:
		return ()

	user = username if hasattr(username,'username') else user_factory( username )
	username = user.username if hasattr(user, 'username') else username # canonicalize

	request = get_current_request() if request is None else request

	key = (username, authenticated)
	if key in getattr(request, '_v_nti_ds_authentication_eff_prin_cache', ()):
		return request._v_nti_ds_authentication_eff_prin_cache[key]

	result = set()
	# Query all the available groups for this user,
	# primary groups (unnamed adapter) and other groups (named adapters)
	for _, adapter in registry.getAdapters( (user,),
											nti_interfaces.IGroupMember ):
		result.update( adapter.groups )

	result.update( _dynamic_memberships_that_participate_in_security( user ) )

	# These last three will be duplicates of string-only versions
	# Ensure that the user is in there as a IPrincipal
	result.update( (nti_interfaces.IPrincipal(username),) )
	# Add the authenticated and everyone groups
	result.add( 'Everyone' )
	result.add( nti_interfaces.IPrincipal( nti_interfaces.EVERYONE_GROUP_NAME ) )

	if authenticated:
		result.add( nti_interfaces.IPrincipal( nti_interfaces.AUTHENTICATED_GROUP_NAME ) )
	if '@' in username:
		# Make the domain portion of the username available as a group
		# TODO: Prefix this, like we do with roles?
		domain = username.split( '@', 1 )[-1]
		if domain:
			result.add( domain )
			result.add( nti_interfaces.IPrincipal( domain ) )

	if request is not None:
		if not hasattr(request, '_v_nti_ds_authentication_eff_prin_cache'):
			request._v_nti_ds_authentication_eff_prin_cache = dict()
		request._v_nti_ds_authentication_eff_prin_cache[key] = result

	return result

@interface.implementer(nti_interfaces.IAuthenticationPolicy)
class _FixedUserAuthenticationPolicy(object):
	"""
	See :func:`Chatserver.send_event_to_user`.
	We implement only the minimum required.
	"""

	def __init__( self, username ):
		self.auth_user = username

	def authenticated_userid( self, request ):
		return self.auth_user

	def effective_principals( self, request ):
		return effective_principals( self.auth_user )

	def _other(self,*args,**kwargs):
		raise NotImplementedError()
	remember = _other
	unauthenticated_userid = _other
	forget = _other

try:
	import gevent.local
	_LocalBase = gevent.local.local
except ImportError:
	import threading
	_LocalBase = threading.local

class _ThreadLocalManager(_LocalBase):
	def __init__(self, default=None):
		_LocalBase.__init__( self )
		self.stack = []
		self.default = default

	def push(self, info):
		self.stack.append(info)

	def pop(self):
		if self.stack:
			return self.stack.pop()

	def get(self):
		"Return the top of the stack, or the default value."
		try:
			return self.stack[-1]
		except IndexError:
			return self.default

class _delegating_descriptor(object):
	"""
	A property-like descriptor that uses the thread-local objects of the given
	instance and returns the value from the top-object on that stack.
	"""
	def __init__( self, name ):
		self.name = name

	def __get__( self, inst, owner ):
		if inst is None:
			return self
		return getattr( inst._locals.get(), self.name )

from zope.security.management import endInteraction
from zope.security.management import newInteraction
from zope.security.management import queryInteraction
from zope.security.interfaces import IParticipation
from zope.security.interfaces import IPrincipal
from zope.security import management

@interface.implementer(IParticipation)
class _Participation(object):

	__slots__ = b'interaction', b'principal' # XXX: Py3

	def __init__( self, principal ):
		self.interaction = None
		self.principal = principal


@interface.implementer(nti_interfaces.IImpersonatedAuthenticationPolicy)
class DelegatingImpersonatedAuthenticationPolicy(object):
	"""
	An implementation of :class:`nti_interfaces.IImpersonatedAuthenticationPolicy`
	that works by delegating all operations to an internal thread-local (greenlet-local)
	stack of contexts. The :meth:`impersonating_userid` method causes a username to be pushed
	and popped from this stack.
	"""

	def __init__( self, base_policy ):
		self._locals = _ThreadLocalManager( default=base_policy )

	def impersonating_userid( self, userid ):
		@contextlib.contextmanager
		def impersonating():
			self._locals.push( _FixedUserAuthenticationPolicy( userid ) )
			# Cannot use restoreInteraction() because we may be nested
			interaction = queryInteraction()
			endInteraction()
			newInteraction(_Participation(IPrincipal(userid)))
			try:
				yield
			finally:
				self._locals.pop()
				endInteraction()
				if interaction is not None:
					management.thread_local.interaction = interaction
		return impersonating

# All the attributes declared on the authentication policy interface
# should delegate
for _x in nti_interfaces.IAuthenticationPolicy:
	setattr( DelegatingImpersonatedAuthenticationPolicy, _x, _delegating_descriptor( _x ) )
