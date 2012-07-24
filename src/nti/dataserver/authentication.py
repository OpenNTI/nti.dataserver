#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes and functions related to authentication.

$Id$
"""
from __future__ import print_function, unicode_literals

import contextlib

from zope import component
from zope import interface

import pyramid.security

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import users

def effective_principals( username,
						  registry=component,
						  authenticated=True,
						  user_factory=users.User.get_user):
	"""
	Find and return the principals for the given username. This will include
	the username itself (obviously), plus a principal for Everyone, plus
	any groups the user is in (as found with :class:`nti_interfaces.IGroupMember`)

	:param username: Either a string giving a username to be looked up,
		or a user object having the ``username`` attribute.
	:param registry: The component registry to query. Defaults to the global
		registry.
	:param bool authenticated: If True (the default) assume this user is properly
		authenticated, and add the pseudo-group for authenticated people as a
		principal.
	:return: An iterable (set) of :class:`nti_interfaces.IPrincipal` objects.
	"""

	if not username:
		return ()

	user = username if hasattr(username,'username') else user_factory( username )
	username = user.username if hasattr(user, 'username') else username # canonicalize

	result = set()
	# Query all the available groups for this user
	for _, adapter in registry.getAdapters( (user,),
											nti_interfaces.IGroupMember ):
		result.update( adapter.groups )

	# Add principals for all the communities that the user is in
	# These are valid ACL targets because they are in the same namespace
	# as users (so no need to prefix with community_ or something like that)
	for community in getattr( user, 'communities', ()): # Mostly tests pass in a non-User user_factory
		# Make sure it's a valid community
		community = users.Entity.get_entity( community )
		if isinstance( community, users.Community ) and not isinstance( community, users.Everyone ): # TODO interface?
			result.add( nti_interfaces.IPrincipal( community ) )

	# These last three will be duplicates of string-only versions
	# Ensure that the user is in there as a IPrincipal
	result.update( (nti_interfaces.IPrincipal(username),) )
	# Add the authenticated and everyone groups
	result.add( nti_interfaces.IPrincipal( pyramid.security.Everyone ) )
	if authenticated:
		result.add( nti_interfaces.IPrincipal( pyramid.security.Authenticated ) )
	if '@' in username:
		# Make the domain portion of the username available as a group
		# TODO: Prefix this, like we do with roles?
		domain = username.split( '@', 1 )[-1]
		result.add( domain )
		result.add( nti_interfaces.IPrincipal( domain ) )
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

import gevent.local

class _ThreadLocalManager(gevent.local.local):
	def __init__(self, default=None):
		gevent.local.local.__init__( self )
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
			try:
				yield
			finally:
				self._locals.pop()
		return impersonating

# All the attributes declared on the authentication policy interface
# should delegate
for _x in nti_interfaces.IAuthenticationPolicy:
	setattr( DelegatingImpersonatedAuthenticationPolicy, _x, _delegating_descriptor( _x ) )
