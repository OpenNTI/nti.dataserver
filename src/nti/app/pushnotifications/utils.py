#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from urllib import urlencode
from urlparse import urljoin

import zope.intid

from zope import component

from itsdangerous import JSONWebSignatureSerializer as SignatureSerializer

from nti.dataserver.users import User

def _signature(username, secret_key):
	s = SignatureSerializer(secret_key)
	signature = s.dumps({'username': username})
	return signature

def validate_signature( user, signature, secret_key=None ):
	"""
	Validate the given signature for the given user, raising
	an exception if the data does not match.
	"""
	username = user.username.lower()
	intids = component.getUtility(zope.intid.IIntIds)

	if not secret_key:
		uid = intids.getId(user)
		secret_key = unicode(uid)

	s = SignatureSerializer(secret_key)
	data = s.loads(signature)

	if data['username'] != username:
		raise ValueError("Invalid token user")

	return data

def generate_signature(user, secret_key=None):
	"""
	Generate a key based on the intid of the user.
	"""
	user = User.get_user(user)
	if user is None:
		raise ValueError("User not found")
	username = user.username.lower()

	intids = component.getUtility(zope.intid.IIntIds)

	if not secret_key:
		uid = intids.getId(user)
		secret_key = unicode(uid)

	result = _signature(username, secret_key)
	return result

def generate_unsubscribe_url(user, request=None, host_url=None, secret_key=None):
	try:
		ds2 = request.path_info_peek() if request else "/dataserver2"
	except AttributeError:
		ds2 = "/dataserver2"

	try:
		host_url = request.host_url if not host_url else None
	except AttributeError:
		host_url = None

	signature = generate_signature(	user=user, secret_key=secret_key)
	params = urlencode({'username': user.username.lower(),
						'signature': signature})

	href = '%s/%s?%s' % (ds2, '@@unsubscribe_digest_email_with_token', params)
	result = urljoin(host_url, href) if host_url else href
	return result
