#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

import time
from urllib import urlencode
from urlparse import urljoin

import zope.intid

from zope import component
from zope import lifecycleevent

from pyramid.view import view_config
from pyramid import httpexceptions as hexc

from itsdangerous import BadSignature
from itsdangerous import JSONWebSignatureSerializer

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserverFolder

from nti.dataserver.users import User
from nti.dataserver.users.interfaces import IUserProfile

from nti.utils.maps import CaseInsensitiveDict

VERIFY_USER_EMAIL_VIEW = "verify_user_email"

def get_user(user):
	result = user if IUser.providedBy(user) else User.get_user(str(user or ''))
	return result

def generate_mail_verification_token(user, timestamp=None, email=None):
	user = get_user(user)
	if user is None:
		raise ValueError("User not found")
	username = user.username.lower()
	
	intids = component.getUtility(zope.intid.IIntIds)
	profile = IUserProfile(user)
	email = email or getattr(profile, 'email', None)
	if not email:
		raise ValueError("User does not have an mail")
	email = email.lower()
	
	# check time stamp
	timestamp = time.time() if timestamp is None else timestamp
	
	uid = intids.getId(user)
	secret_key = unicode(uid) 
	s = JSONWebSignatureSerializer(secret_key)
	token = s.dumps({'email': email,
					 'username': username,
			 		 'timestamp': timestamp})
	return token
	
def get_verification_token_data(user, token, params=None, email=None):
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
	
	uid = intids.getId(user)
	secret_key = unicode(uid) 
	s = JSONWebSignatureSerializer(secret_key)
	data = s.loads(token)
	
	if data['username'] != username:
		raise ValueError("Invalid token user")
	
	if data['email'] != email:
		raise ValueError("Invalid token email")
	return data

def generate_verification_email_url(user, request=None, host_url=None,
									timestamp=None, email=None):
	
	try:
		ds2 = request.path_info_peek() if request else "/dataserver2"
	except AttributeError:
		ds2 = "/dataserver2"
		
	token = generate_mail_verification_token(user, timestamp=timestamp, email=email)
	params = urlencode({'username': user.username.lower(), 'token': token})
	
	href = '/%s/%s?%s' % (ds2, VERIFY_USER_EMAIL_VIEW, params)
	result = host_url or request.host_url
	result = urljoin(result, href)
	return result
		
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
		token = values.get('token')
		if not token:
			raise hexc.HTTPUnprocessableEntity(_("No token specified"))
		
		username = values.get('username')
		if not username:
			raise hexc.HTTPUnprocessableEntity(_("No username specified"))
		user = get_user(username)
		if user is None:
			raise hexc.HTTPUnprocessableEntity(_("User not found"))
		
		try:
			get_verification_token_data(user, token, params=values)
		except BadSignature:
			raise hexc.HTTPUnprocessableEntity(_("Invalid token signature"))
		except ValueError as e:
			msg = _(str(e))
			raise hexc.HTTPUnprocessableEntity(msg)
		
		self.request.environ[b'nti.request_had_transaction_side_effects'] = b'True'
		IUserProfile(user).email_verified = True
		lifecycleevent.modified(user)
		
		return_url = values.get('return_url')
		if return_url:
			return hexc.HTTPFound(location=return_url)
		return hexc.HTTPNoContent()
