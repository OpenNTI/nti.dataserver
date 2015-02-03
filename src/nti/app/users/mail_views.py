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

from zope import lifecycleevent

from pyramid.view import view_config
from pyramid import httpexceptions as hexc

from itsdangerous import BadSignature

from nti.app.base.abstract_views import AbstractAuthenticatedView
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.common.maps import CaseInsensitiveDict

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserverFolder

from nti.dataserver.users import User
from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import checkEmailAddress
from nti.dataserver.users.interfaces import EmailAddressInvalid

from . import VERIFY_USER_EMAIL_VIEW
from . import REQUEST_EMAIL_VERFICATION_VIEW
from . import SEND_USER_EMAIL_VERFICATION_VIEW
from . import VERIFY_USER_EMAIL_WITH_TOKEN_VIEW

from .utils import get_user
from .utils import get_email_verification_time
from .utils import safe_send_email_verification
from .utils import generate_mail_verification_pair
from .utils import get_verification_signature_data

@view_config(route_name='objects.generic.traversal',
			 name=VERIFY_USER_EMAIL_VIEW,
			 request_method='GET',
			 context=IDataserverFolder)
class VerifyUserEmailView(object):

	def __init__(self, request):
		self.request = request
		
	def __call__(self):
		request = self.request
		values = CaseInsensitiveDict(**request.params)
		signature = values.get('signature') or values.get('token')
		if not signature:
			raise hexc.HTTPUnprocessableEntity(_("No signature specified."))
		
		username = values.get('username')
		if not username:
			raise hexc.HTTPUnprocessableEntity(_("No username specified."))
		user = get_user(username)
		if user is None:
			raise hexc.HTTPUnprocessableEntity(_("User not found."))
		
		try:
			get_verification_signature_data(user, signature, params=values)
		except BadSignature:
			raise hexc.HTTPUnprocessableEntity(_("Invalid signature."))
		except ValueError as e:
			msg = _(str(e))
			raise hexc.HTTPUnprocessableEntity(msg)
		
		self.request.environ[b'nti.request_had_transaction_side_effects'] = b'True'
		IUserProfile(user).email_verified = True
		lifecycleevent.modified(user) # make sure we update the index
		
		return_url = values.get('return_url')
		if return_url:
			return hexc.HTTPFound(location=return_url)
		return hexc.HTTPNoContent()

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
		
		_, computed = generate_mail_verification_pair(self.remoteUser)
		if token != computed:
			raise hexc.HTTPUnprocessableEntity(_("Wrong token."))
		
		IUserProfile(self.remoteUser).email_verified = True
		lifecycleevent.modified(self.remoteUser)  # make sure we update the index
		return hexc.HTTPNoContent()

@view_config(route_name='objects.generic.traversal',
			 name=REQUEST_EMAIL_VERFICATION_VIEW,
			 request_method='POST',
			 context=IUser,
			 renderer='rest',
			 permission=nauth.ACT_UPDATE)
class RequestEmailVerificationView(	AbstractAuthenticatedView, 
									ModeledContentUploadRequestUtilsMixin):
		
	def __call__(self):
		user = self.remoteUser
		profile = IUserProfile(user)
		email = CaseInsensitiveDict(self.readInput()).get('email')
		if email:
			try:
				checkEmailAddress(email)
				profile.email = email
				profile.email_verified = False
				lifecycleevent.modified(user)
			except (EmailAddressInvalid):
				raise hexc.HTTPUnprocessableEntity(_("Invalid email address."))
		else:
			email = profile.email
			
		if profile.email_verified:
			now  = time.time()
			last_time = get_email_verification_time(user) or 0
			if now - last_time > 3600: # wait an hour
				safe_send_email_verification(user, profile, email, self.request)
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
		usernames = values.get('usernames') or values.get('usernane')
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
			safe_send_email_verification(user, profile, email, self.request)
			# wait a bit
			gevent.sleep(0.5)
		return hexc.HTTPNoContent()
