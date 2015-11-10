#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pyramid authentication policy based on :mod:`repoze.who` and :mod:`pyramid_who`.

As-of Pyramid 1.5, the basic auth and auth_tkt support is available in
Pyramid's core; however, stacking them to work together requires
third-party code (pyramid_multiauth) that may be less flexible and may work
less well in a Zope-ish environment.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from zope import component
from zope import interface
from zope.authentication import interfaces

from pyramid.interfaces import IAuthenticationPolicy
from pyramid_who.whov2 import WhoV2AuthenticationPolicy

from nti.dataserver.authentication import effective_principals
from .who_authenticators import ANONYMOUS_USERNAME

ONE_DAY = 24 * 60 * 60
ONE_WEEK = 7 * ONE_DAY

class _GroupsCallback(object):
	"""
	A callback for the pyramid effective principals for a user.
	"""
	__slots__ = ()

	def __call__( self, identity, request ):
		"""
		Callback method for :mod:`pyramid_who`. We are guaranteed to
		only be called when an :class:`.IAuthenticator` has matched;
		we get the last say, as returning None from this callback
		causes :meth:`.authenticated_userid` to also return None.
		"""
		# NOTE: we are caching the group results as part of the userid dictionary,
		# which means they cannot change during a request.
		CACHE_KEY = 'nti.dataserver.groups'
		if CACHE_KEY in identity:
			return identity[CACHE_KEY]

		username = None
		if 'repoze.who.userid' in identity: # already identified by AuthTktCookie or _NTIUsersAuthenticatorPlugin
			username = identity['repoze.who.userid']

		# Check if we have been identifies as the anonymous user
		# XXX: Question. We could also check that identity['identifier'] is an instance of
		# our AnonymousAccessAuthenticator class.  Is that necessary
		if username == ANONYMOUS_USERNAME or username == None:
			return ( component.getUtility( interfaces.IUnauthenticatedPrincipal ), )


		result = effective_principals( username,
									   registry=request.registry,	
									   authenticated=True,
									   request=request )

		identity[CACHE_KEY] = result
		return result

@interface.implementer(IAuthenticationPolicy)
class AuthenticationPolicy(WhoV2AuthenticationPolicy):

	def __init__( self, identifier_id,  #pylint: disable=I0011,W0231
				  cookie_timeout=ONE_WEEK,
				  api_factory=None ):
		"""
		:param identifier_id: The name of the fallback identifier to use
			if we are asked to remember something but haven't
			authenticated yet.
		"""
		# NOTE: We do not call super to avoid emitting useless warnings
		self._identifier_id = identifier_id
		self._callback = _GroupsCallback()
		self._api_factory = api_factory
		self._cookie_timeout = cookie_timeout

	# Note that the auth tkt never gets reissued; unlike repoze.who's
	# `login` function, nothing in pyramid ever calls `remember`
	# automatically. The version of auth_tkt that comes with Pyramid
	# (AuthTktCookieHelper) handles this by reissuing the cooking at
	# `identify` time (actually, it schedules a response callback),
	# and the policy that uses it calls this method from all of
	# `authenticated_userid`, `unauthenticated_userid` and
	# `effective_principals` (in fact, they all call through to
	# `unauthenticated_userid` which in turn calls `identify`). We
	# replicate this behaviour by doing the same thing, but that takes
	# overriding each method, sadly.

	def unauthenticated_userid(self, request):
		res = super(AuthenticationPolicy,self).unauthenticated_userid(request)
		if res:
			self.__do_reissue(request)
		return res

	def authenticated_userid(self, request):
		res = super(AuthenticationPolicy,self).authenticated_userid(request)
		if res:
			self.__do_reissue(request)
		return res

	def effective_principals(self, request):
		res = super(AuthenticationPolicy,self).effective_principals(request)
		if res and len(res) > 1:
			self.__do_reissue(request)
		return res

	def __do_reissue(self, request):
		if hasattr(request, '_authtkt_reissued'):
			# already checked all this, bail
			return

		identity = self._get_identity(request)
		if not identity or 'timestamp' not in identity:
			# If we're not identified or (piggybacking on implementation
			# details of the Auth_tkt plugin) we're not identified
			# by an auth_tkt, bail
			return

		api = self._getAPI(request)
		identifier = api.name_registry[self._identifier_id]
		if identity.get('identifier') != identifier:
			# if we're not the auth_tkt, bail
			return

		if identifier.reissue_time is None:
			# not asked to reissue, bail
			return

		now = time.time()
		if (now - identity['timestamp']) <= identifier.reissue_time:
			# Still good
			return

		if 'max_age' not in identity:
			identity['max_age'] = str(self._cookie_timeout)

		headers = identifier.remember(request.environ, identity)
		def reissue(request, response):
			if hasattr(request, '_authtkt_reissue_revoked'):
				return
			for k, v in headers:
				response.headerlist.append( (k, v) )
		request.add_response_callback(reissue)
		request._authtkt_reissued = True


	def forget(self, request):
		request._authtkt_reissue_revoked = True
		return super(AuthenticationPolicy,self).forget(request)

	def remember(self, request, principal, **kw):
		res = self.__do_remember(request, principal, **kw)
		# Match what pyramid's AuthTkt policy does
		if hasattr(request, '_authtkt_reissued'):
			request._authtkt_reissue_revoked = True

		return res

	def __do_remember(self, request, principal, **kw):
		# The superclass hardcodes the dictionary that is used
		# for the identity. This identity is passed to the plugins.
		# This has at least three problems:
		#
		# The first is that the identifier that actually identified
		# the principal is not used, instead it is hardcoded to
		# self._identifier_id (this only matters if we're remembering
		# the same user); note, however, that we need to be careful
		# about reusing this if we were identified via an IIdentifier
		# that doesn't actually remember.
		#
		# Second, the AuthTkt plugin will only set cookie expiration
		# headers right if a max_age is included in the identity.
		#
		# Third, for the auth tkt to also be able to set
		# REMOTE_USER_DATA and REMOTE_USER_TOKENS, those also need to
		# come in as 'tokens' and 'userdata' (which is what it would
		# have been set to initially by that plugin). Our code will
		# generally set REMOTE_USER_DATA/REMOTE_USER_TOKENS directly,
		# so we copy them to the identity specifically. The tokens is
		# a tuple of (native) strings, while userdata is a single
		# string.
		#
		# We fix both issues here

		api = self._getAPI(request)
		identity = (self._get_identity(request) or {}).copy()
		fake_identity = {
			'repoze.who.userid': principal,
			'max_age': str(self._cookie_timeout),
			'tokens': request.environ.get('REMOTE_USER_TOKENS', ()),
			'userdata': request.environ.get('REMOTE_USER_DATA', b'')
			}
		if (principal != identity.get('repoze.who.userid') # start from scratch for a changed user
			or 'identifier' not in identity # also from scratch, remembering unconditionally, usually from app code
			or 'AUTH_TYPE' not in request.environ): # also from scratch (typically basic auth)
			fake_identity['identifier'] = api.name_registry[self._identifier_id]
		identity.update(fake_identity)
		return api.remember(identity)
