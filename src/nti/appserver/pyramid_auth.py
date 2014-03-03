#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__ )

from zope import interface
from zope import component

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import authentication as nti_authentication
from nti.dataserver import authorization as nti_authorization


from .interfaces import IUserViewTokenCreator

from nti.app.authentication.interfaces import IIdentifiedUserTokenAuthenticator

@interface.implementer(IUserViewTokenCreator)
class _UserViewTokenCreator(object):

	def __init__(self, secret):
		self.secret = secret

	def getTokenForUserId( self, userid ):
		"""
		Given a logon for a user, return a token that can be
		used to identify the user in the future. If the user
		does not exist or cannot get a token, return None.
		"""
		return component.getAdapter(self.secret,IIdentifiedUserTokenAuthenticator).getTokenForUserId(userid)

ONE_DAY = 24 * 60 * 60
ONE_WEEK = 7 * ONE_DAY
ONE_MONTH = 30 * ONE_DAY

from nti.app.authentication.who_policy import AuthenticationPolicy
from nti.app.authentication.who_apifactory import create_who_apifactory
from nti.app.authentication.who_views import ForbiddenView

def configure_authentication_policy( pyramid_config,
									 secure_cookies=True,
									 cookie_secret='$Id$',
									 cookie_timeout=ONE_WEEK ):
	"""
	Create and configure the authentication policy and the things that go with it.

	:param bool secure_cookies: If ``True`` (the default), then any cookies
		we create will only be sent over SSL and will additionally have the 'HttpOnly'
		flag set, preventing them from being subject to cross-site vulnerabilities.
		This must be explicitly turned off if not desired.
	:param str cookie_secret: The value used to encrypt cookies. Must be the same on
		all instances in a given environment, but should be different in different
		environments.
	"""
	token_allowed_views = ('feed.rss', 'feed.atom')
	api_factory = create_who_apifactory(secure_cookies=secure_cookies,
										cookie_secret=cookie_secret,
										cookie_timeout=cookie_timeout,
										token_allowed_views=token_allowed_views)
	policy = AuthenticationPolicy(api_factory.default_identifier_name,
								  cookie_timeout=cookie_timeout,
								  api_factory=api_factory)
	# And make it capable of impersonation
	policy = nti_authentication.DelegatingImpersonatedAuthenticationPolicy( policy )


	pyramid_config.set_authentication_policy( policy )
	pyramid_config.add_forbidden_view( ForbiddenView() )

	user_token_creator = _UserViewTokenCreator(cookie_secret)
	for view_name in token_allowed_views:
		pyramid_config.registry.registerUtility( user_token_creator,
												 IUserViewTokenCreator,
												 name=view_name )
	pyramid_config.registry.registerUtility(api_factory)


@interface.implementer(nti_interfaces.IGroupMember)
@component.adapter(nti_interfaces.IUser)
class NextthoughtDotComAdmin(object):
	"""
	Somewhat hackish way to grant the admin role to any account in @nextthought.com
	"""

	def __init__( self, context ):
		self.groups = (nti_authorization.ROLE_ADMIN,) if context.username.endswith( '@nextthought.com' ) else ()
