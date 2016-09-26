#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Plugins for :mod:`repoze.who` that primarily handle authentication.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.pluggableauth.interfaces import IAuthenticatorPlugin

from repoze.who.interfaces import IIdentifier
from repoze.who.interfaces import IAuthenticator

from nti.app.authentication.interfaces import IIdentifiedUserTokenAuthenticator

@interface.implementer(IAuthenticator)
class DataserverGlobalUsersAuthenticatorPlugin(object):

	def authenticate(self, environ, identity):
		try:
			plugin = component.getUtility(IAuthenticatorPlugin,
										  name="Dataserver Global User Authenticator")
			return plugin.authenticateCredentials(identity).id
		except (KeyError, AttributeError, LookupError):  # pragma: no cover
			return None

@interface.implementer(IAuthenticator,
					   IIdentifier)
class KnownUrlTokenBasedAuthenticator(object):
	"""
	A :mod:`repoze.who` plugin that acts in the role of identifier
	(determining who the remote user is claiming to be)
	as well as authenticator (matching the claimed remote credentials
	to the real credentials). This information is not sent in the
	headers (Authenticate or Cookie) but instead, for the use of
	copy-and-paste, retrieved directly from query parameters in the
	URL (specifically, the 'token' parameter).

	Because it is part of the URL, this information is visible in the
	logs for the entire HTTP pipeline. To limit the overuse of this, we
	only want to allow it for particular URLs, as based on the path.
	"""

	# We actually piggyback off the authtkt implementation, using
	# a version of the user's password as the 'user data'

	from paste.request import parse_dict_querystring
	parse_dict_querystring = staticmethod(parse_dict_querystring)

	def __init__(self, secret, allowed_views=()):
		"""
		Creates a combo :class:`.IIdentifier` and :class:`.IAuthenticator`
		using an auth-tkt like token.

		:param string secret: The encryption secret. May be the same as the
			auth_tkt secret.
		:param sequence allowed_views: A set of view names (final path sequences)
			that will be allowed to be authenticated by this plugin.
		"""
		self.secret = secret
		self.allowed_views = allowed_views

	def identify(self, environ):
		# Obviously if there is no token we can't identify
		if b'QUERY_STRING' not in environ or b'token' not in environ[b'QUERY_STRING']:
			return
		if b'PATH_INFO' not in environ:
			return
		if not any((environ['PATH_INFO'].endswith(view) for view in self.allowed_views)):
			return

		query_dict = self.parse_dict_querystring(environ)
		token = query_dict['token']
		identity = component.getAdapter(self.secret, IIdentifiedUserTokenAuthenticator).getIdentityFromToken(token)
		if identity is not None:
			environ['IDENTITY_TYPE'] = 'token'
		return identity

	def forget(self, environ, identity):  # pragma: no cover
		return []
	def remember(self, environ, identity):  # pragma: no cover
		return []

	def authenticate(self, environ, identity):
		if environ.get('IDENTITY_TYPE') != 'token':
			return

		environ[b'AUTH_TYPE'] = b'token'
		return component.getAdapter(self.secret, IIdentifiedUserTokenAuthenticator).identityIsValid(identity)


@interface.implementer(IAuthenticator, IIdentifier)
class FixedUserAuthenticatorPlugin(object):  # pragma: no cover # For use with redbot testing

	username = 'pacifique.mahoro@nextthought.com'

	def authenticate(self, environ, identity):
		return self.username

	def identify(self, environ):
		return {'login': self.username}

	def remember(self, *args):
		return ()

	def forget(self, *args):
		return ()
