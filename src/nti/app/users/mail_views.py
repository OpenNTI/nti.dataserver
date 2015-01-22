#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

import hashlib
from urllib import urlencode
from urlparse import urljoin

import zope.intid

from zope import component
from zope import lifecycleevent

from pyramid.view import view_config
from pyramid import httpexceptions as hexc

from itsdangerous import BadSignature
from itsdangerous import JSONWebSignatureSerializer as SignatureSerializer

from nti.app.base.abstract_views import AbstractAuthenticatedView
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserverFolder

from nti.dataserver.users import User
from nti.dataserver.users.interfaces import IUserProfile

from nti.utils.maps import CaseInsensitiveDict

VERIFY_USER_EMAIL_VIEW = "verify_user_email"
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
	return result, signature, token
		
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
