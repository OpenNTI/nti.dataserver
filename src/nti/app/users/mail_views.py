#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

import six
import time
import gevent
import urllib

from urlparse import urljoin

from zope import component

from pyramid.view import view_config
from pyramid.renderers import render
from pyramid import httpexceptions as hexc

from itsdangerous import BadSignature

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error as raise_error
from nti.app.externalization.internalization import read_body_as_external_object
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.appserver.interfaces import IApplicationSettings

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.appserver.policies.site_policies import guess_site_display_name

from nti.common.maps import CaseInsensitiveDict

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserverFolder

from nti.dataserver.users import User
from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import checkEmailAddress
from nti.dataserver.users.interfaces import EmailAddressInvalid
from nti.dataserver.users.utils import reindex_email_verification

from . import VERIFY_USER_EMAIL_VIEW
from . import REQUEST_EMAIL_VERFICATION_VIEW
from . import SEND_USER_EMAIL_VERFICATION_VIEW
from . import VERIFY_USER_EMAIL_WITH_TOKEN_VIEW

from .utils import get_email_verification_time
from .utils import safe_send_email_verification
from .utils import generate_mail_verification_pair
from .utils import get_verification_signature_data

MAX_WAIT_TIME_EMAILS = 300

def _login_root():
	settings = component.getUtility(IApplicationSettings)
	login_root = settings.get('login_app_root', '/login/')
	return login_root

@view_config(route_name='objects.generic.traversal',
			 name=VERIFY_USER_EMAIL_VIEW,
			 request_method='GET',
			 context=IDataserverFolder)
class VerifyUserEmailView( AbstractAuthenticatedView ):

	def process_verification(self, user, signature, values):
		try:
			get_verification_signature_data(user, signature, params=values)
		except BadSignature:
			raise hexc.HTTPUnprocessableEntity(_("Invalid signature."))
		except ValueError as e:
			msg = _(str(e))
			raise hexc.HTTPUnprocessableEntity(msg)

		self.request.environ[b'nti.request_had_transaction_side_effects'] = b'True'
		IUserProfile(user).email_verified = True
		reindex_email_verification(user)

	def __call__(self):
		request = self.request
		user = self.remoteUser

		if user is None:
			# If unauthenticated, redirect to login with redirect to this view.
			# This seems generic enough that we would want to do
			# this for all authenticated views (or the BrowserRedirectorPlugin).
			login_root = _login_root()

			current_path = request.current_route_path()
			current_path = urllib.quote( current_path )
			return_url = "%s?return=%s" % (login_root, current_path)
			return hexc.HTTPFound( location=return_url )

		values = CaseInsensitiveDict(**request.params)
		signature = values.get('signature') or values.get('token')
		if not signature:
			# TODO We should move this below to our template handling
			raise hexc.HTTPUnprocessableEntity(_("No signature specified."))

		destination_url = urljoin( self.request.application_url, _login_root() )
		template_args = {'href': destination_url}

		policy = component.getUtility(ISitePolicyUserEventListener)
		support_email = getattr( policy, 'SUPPORT_EMAIL', 'support@nextthought.com' )
		template_args['support_email'] = support_email
		template_args['error_message'] = None
		template_args['site_name'] = guess_site_display_name(self.request)
		try:
			self.process_verification(user, signature, values)
		except hexc.HTTPError as e:
			logger.info('Account verification for user "%s" failed. %s',
					user,
					getattr(e, 'detail', ''))
			template_args['error_message'] = _("Unable to verify account.")

		# TODO Should make this conditional
		self.request.environ[ 'HTTP_X_REQUESTED_WITH' ] = str( 'xmlhttprequest' )

		result = render( "templates/email_verification_completion_page.pt",
						 template_args,
						 request=self.request )

		response = self.request.response
		response.content_type = str( 'text/html' )
		response.content_encoding = str('identity' )
		response.text = result

		return response

@view_config(route_name='objects.generic.traversal',
			 name=VERIFY_USER_EMAIL_WITH_TOKEN_VIEW,
			 request_method='POST',
			 context=IDataserverFolder)
class VerifyUserEmailWithTokenView(	AbstractAuthenticatedView,
									ModeledContentUploadRequestUtilsMixin):

	def __call__(self):
		values = CaseInsensitiveDict(self.readInput())
		token = values.get('hash') or values.get('token')
		if not token:
			raise hexc.HTTPUnprocessableEntity(_("No token specified."))

		try:
			token = int(token)
		except (TypeError, ValueError):
			raise hexc.HTTPUnprocessableEntity(_("Invalid token."))

		sig, computed = generate_mail_verification_pair(self.remoteUser)
		if token != computed:
			__traceback_info__ = sig, computed
			raise hexc.HTTPUnprocessableEntity(_("Wrong token."))

		IUserProfile(self.remoteUser).email_verified = True
		reindex_email_verification(self.remoteUser)
		return hexc.HTTPNoContent()

@view_config(route_name='objects.generic.traversal',
			 name=REQUEST_EMAIL_VERFICATION_VIEW,
			 request_method='POST',
			 context=IUser,
			 renderer='rest',
			 permission=nauth.ACT_UPDATE)
class RequestEmailVerificationView(	AbstractAuthenticatedView,
									ModeledContentUploadRequestUtilsMixin):

	def readInput(self, value=None):
		if self.request.body:
			values = read_body_as_external_object( self.request )
		else:
			values = self.request.params
		result = CaseInsensitiveDict( values )
		return result

	def __call__(self):
		user = self.remoteUser
		profile = IUserProfile(user)
		email = self.readInput().get('email')
		if email:
			try:
				checkEmailAddress(email)
				profile.email = email
				profile.email_verified = False
				reindex_email_verification(user)
			except (EmailAddressInvalid):
				raise hexc.HTTPUnprocessableEntity(_("Invalid email address."))
		else:
			email = profile.email

		if email is None:
			raise hexc.HTTPUnprocessableEntity(_("Email address not provided."))

		if not profile.email_verified:
			now  = time.time()
			last_time = get_email_verification_time(user) or 0
			diff_time = now - last_time
			if diff_time > MAX_WAIT_TIME_EMAILS:
				safe_send_email_verification(user, profile, email, self.request)
			else:
				raise_error(self.request,
							hexc.HTTPUnprocessableEntity,
							{ 'message': _("A current request is been processed." ),
							  'seconds': MAX_WAIT_TIME_EMAILS - diff_time },
							None )
		return hexc.HTTPNoContent()

@view_config(route_name='objects.generic.traversal',
			 name=SEND_USER_EMAIL_VERFICATION_VIEW,
			 request_method='POST',
			 context=IDataserverFolder,
			 permission=nauth.ACT_NTI_ADMIN)
class SendUserEmailVerificationView(AbstractAuthenticatedView,
									ModeledContentUploadRequestUtilsMixin):

	def __call__(self):
		values = CaseInsensitiveDict(self.readInput())
		usernames = values.get('usernames') or values.get('username')
		if not usernames:
			raise hexc.HTTPUnprocessableEntity(_("No must specify a username."))
		if isinstance(usernames, six.string_types):
			usernames = usernames.split(',')

		for username in usernames:
			user = User.get_user(username)
			if not user:
				continue
			# send email
			profile = IUserProfile(user, None)
			email = getattr(profile, 'email', None)
			email_verified =  getattr(profile, 'email_verified', False)
			if not email_verified:
				safe_send_email_verification(user, profile, email, self.request)
			else:
				logger.debug("Not sending email verification to %s", user)
			# wait a bit
			gevent.sleep(0.5)
		return hexc.HTTPNoContent()
