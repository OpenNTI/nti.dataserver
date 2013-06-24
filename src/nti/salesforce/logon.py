# -*- coding: utf-8 -*-
"""
Salesforce login routines

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import urllib
import requests

from pyramid import security as sec
from pyramid.view import view_config
from pyramid import httpexceptions as hexc

from zope.event import notify

from nti.dataserver.users import User

from . import chatter
from . import users as sf_users
from . import interfaces as sf_interfaces

TOKEN_URL = u'https://na1.salesforce.com/services/oauth2/token'
AUTHORIZE_URL = u'https://na1.salesforce.com/services/oauth2/authorize'

def response_token_by_username_password(client_id, client_secret, security_token, username, password):
	"""
	return a response token using a Username-password flow.
	this is not recommended for production app
	"""
	payload = {u'client_id':client_id, u'client_secret':client_secret, 'grant_type':'password',
			   u'username':username, u'password':'%s%s' % (password, security_token) }
	r = requests.post(TOKEN_URL, data=payload)
	data = r.json()
	assert r.status_code == 200
	assert u'error' not in data, data.get(u'error_description', data.get(u'error'))
	return data
	
def _check_error(request, params):
	error = params.get('error')
	error_description = params.get('error_description', error)
	if error:
		response = hexc.HTTPBadRequest()
		response.headers.extend(sec.forget(request))
		response.headers[b'Warning'] = error_description.encode('utf-8')
		return response
	return None

@view_config(route_name='logon.salesforce.oauth', request_method='GET')
def salesforce_oauth1(request):
	params = request.params
	error_response = _check_error(request, params)
	if error_response:
		return error_response

	if 'access_token' in params:
		return salesforce_oauth2(request, params)
	else:
		app = chatter.get_salesforce_app(request)
		code = params['code']
		our_uri = urllib.quote(request.route_url('logon.salesforce.oauth'))
		post_to = '%s?grant_type=authorization_code&code=%s&client_secret=%s&client_id=%s&redirect_uri=%s' % \
					(TOKEN_URL, code, app.ClientSecret, app.ClientID, our_uri)

		r = requests.post(post_to)
		return salesforce_oauth2(request, r.json())

def salesforce_oauth2(request, params):

	error_response = _check_error(request, params)
	if error_response:
		return error_response

	response_token = params
	access_token = response_token['access_token']
	instance_url = response_token['instance_url']

	# make sure we have a internal user
	user_info = chatter.get_chatter_user(instance_url, access_token)
	username = user_info['username']
	user = User.get_user(username)
	if user is None:
		ext_value = {}
		if user_info.get('firstName') and user_info.get('lastName'):
			ext_value['realname'] = '%s %s' % (user_info['firstName'], user_info['lastName'])
		if user_info.get('email'):
			ext_value['email'] = user_info.get('email')
		# create user
		identity_url = user_info.get('id')
		user = sf_users.SalesforceUser.create_user(username=username, identity_url=identity_url, external_value=ext_value)
		logger.debug("User '%s' has been created" % username)
		
	# record token
	sf = sf_interfaces.ISalesforceTokenInfo(user)
	sf.AccessToken = response_token['access_token']
	sf.RefreshToken = response_token['refresh_token']
	sf.InstanceURL = response_token['instance_url']
	sf.Signature = response_token['signature']

	# login process

	from nti.appserver import interfaces as app_interfaces
	response = hexc.HTTPNoContent()
	request.response = response

	notify(app_interfaces.UserLogonEvent(user, request))

	response.headers.extend(sec.remember(request, user.username.encode('utf-8')))
	response.set_cookie(b'username', user.username.encode('utf-8'))  # the

	return response
