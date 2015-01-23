#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

import os
import six
import time
import isodate
import hashlib
import datetime
from urllib import urlencode
from urlparse import urljoin

import gevent

import zope.intid

from zope import component
from zope import lifecycleevent

from zope.annotation.interfaces import IAnnotations

from zope.dottedname import resolve as dottedname

from zope.i18n import translate

from zope.security.interfaces import IPrincipal

from pyramid.view import view_config
from pyramid import httpexceptions as hexc

from itsdangerous import BadSignature
from itsdangerous import JSONWebSignatureSerializer as SignatureSerializer

from nti.app.base.abstract_views import AbstractAuthenticatedView
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserverFolder

from nti.dataserver.users import User
from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IEmailAddressable

from nti.externalization.externalization import to_external_object

from nti.mailer.interfaces import ITemplatedMailer

from nti.utils.maps import CaseInsensitiveDict

VERIFY_USER_EMAIL_VIEW = "verify_user_email"
SEND_USER_EMAIL_VERFICATION_VIEW = "send_user_email_verification"
VERIFY_USER_EMAIL_WITH_TOKEN_VIEW = "verify_user_email_with_token"

def get_user(user):
	result = user if IUser.providedBy(user) else User.get_user(str(user or ''))
	return result

def _token(signature):
	token = int(hashlib.sha1(signature).hexdigest(), 16) % (10 ** 8)
	return token

def _signature_and_token(username, email, secret_key):
	s = SignatureSerializer(secret_key)
	signature = s.dumps({'email': email, 'username': username})
	token = _token(signature)
	return signature, token

def generate_mail_verification_pair(user, email=None, secret_key=None):
	user = get_user(user)
	if user is None:
		raise ValueError("User not found")
	username = user.username.lower()
	
	intids = component.getUtility(zope.intid.IIntIds)
	profile = IUserProfile(user, None)
	email = email or getattr(profile, 'email', None)
	if not email:
		raise ValueError("User does not have an mail")
	email = email.lower()
	
	if not secret_key:
		uid = intids.getId(user)
		secret_key = unicode(uid) 
		
	result = _signature_and_token(username, email, secret_key)
	return result
	
def get_verification_signature_data(user, signature, params=None, 
									email=None, secret_key=None):
	user = get_user(user)
	if user is None:
		raise ValueError("User not found")
	username = user.username.lower()
	
	intids = component.getUtility(zope.intid.IIntIds)
	profile = IUserProfile(user)
	email = email or getattr(profile, 'email', None)
	if not email:
		raise ValueError("User does not have an email")
	email = email.lower()
	
	if not secret_key:
		uid = intids.getId(user)
		secret_key = unicode(uid) 
		
	s = SignatureSerializer(secret_key)
	data = s.loads(signature)
	
	if data['username'] != username:
		raise ValueError("Invalid token user")
	
	if data['email'] != email:
		raise ValueError("Invalid token email")
	return data

def generate_verification_email_url(user, request=None, host_url=None,
									email=None, secret_key=None):
	try:
		ds2 = request.path_info_peek() if request else "/dataserver2"
	except AttributeError:
		ds2 = "/dataserver2"
		
	try:
		host_url = request.host_url if not host_url else None
	except AttributeError:
		host_url = None
		
	signature, token = generate_mail_verification_pair(	user=user, email=email,
														secret_key=secret_key)
	params = urlencode({'username': user.username.lower(), 
						'signature': signature})
	
	href = '%s/%s?%s' % (ds2, '@@'+VERIFY_USER_EMAIL_VIEW, params)
	result = urljoin(host_url, href) if host_url else href
	return result, token
		
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

## Email

_EMAIL_VERIFICATION_TIME_KEY = 'nti.app.users._EMAIL_VERIFICATION_TIME_KEY'

def _get_email_verification_time_key(user):
	annotes = IAnnotations(user)
	result = annotes.get(_EMAIL_VERIFICATION_TIME_KEY)
	return result

def _set_email_verification_time_key(user, now=None):
	now = now or time.time()
	annotes = IAnnotations(user)
	annotes[_EMAIL_VERIFICATION_TIME_KEY] = now

def _get_package(policy, template='email_verification_email'):
	base_package = 'nti.app.users' 
	package = getattr(policy, 'PACKAGE', None)
	if not package:
		package = base_package
	else:
		package = dottedname.resolve(package)
		path = os.path.join(os.path.dirname(package.__file__), 'templates')
		if not os.path.exists(os.path.join(path, template + ".pt")):
			package = base_package
	return package

def _send_email_email_verification(user, profile, email, request=None):
	if not request or not email:
		logger.warn("Not sending email to %s because of no email or request", user)
		return
	
	username = user.username
	policy = component.getUtility(ISitePolicyUserEventListener)

	assert getattr(IPrincipal(profile, None), 'id', None) == user.username
	assert getattr(IEmailAddressable(profile, None), 'email', None) == email

	user_ext = to_external_object(user)
	informal_username = user_ext.get('NonI18NFirstName', profile.realname) or username

	site_alias = getattr(policy, 'COM_ALIAS', '')
	support_email = getattr(policy, 'SUPPORT_EMAIL', 'support@nextthought.com')
	href, token = generate_verification_email_url(user, request=request)
	
	args = {'user': user,
			'href' : href,
			'token': token,
			'profile': profile,
			'request': request,
			'brand': policy.BRAND,
			'site_alias': site_alias,
			'support_email': support_email,
			'informal_username': informal_username,
			'today': isodate.date_isoformat(datetime.datetime.now()) }

	template = 'email_verification_email'
	package = _get_package(policy, template=template)
	
	logger.info("Sending email verification to %s", user)
	
	mailer = component.getUtility(ITemplatedMailer)
	mailer.queue_simple_html_text_email(
				template,
				subject=translate(_("Email Confirmation")),
				recipients=[profile],
				template_args=args,
				request=request,
				package=package)

	# record time
	_set_email_verification_time_key(user)
	
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
			profile = IUserProfile(user, None)
			email = getattr(profile, 'email', None)
			_send_email_email_verification(user, profile, email, self.request)
			gevent.sleep(0.5)
		return hexc.HTTPNoContent()


# @component.adapter(ICourseInstanceEnrollmentRecord, IObjectAddedEvent)
# def _enrollment_added(record, event):
# 	# We only want to do this when the user initiated the event,
# 	# not when it was done via automatic workflow.
# 	if queryInteraction() is None:
# 		# no interaction, no email
# 		return
# 
# 	# For now, the easiest way to detect that is to know that
# 	# automatic workflow is the only way to enroll in ES_CREDIT_DEGREE.
# 	# We also want a special email for 5-ME, so we avoid those as well.
# 	if record.Scope != ES_PUBLIC:
# 		return
# 
# 	creator = event.object.Principal
# 	profile = IUserProfile(creator)
# 	email = getattr(profile, 'email', None)
# 
# 	# Exactly one course at a time
# 	course = record.CourseInstance
# 	_send_enrollment_confirmation(event, creator, profile, email, course)