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
from pyramid.threadlocal import get_current_request

from zope import component

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

def refresh_token(client_id, refresh_token, client_secret=None):
	"""
	send a request for a new access token.
	"""
	payload = {u'client_id':client_id, 'grant_type':'refresh_token', u'refresh_token':refresh_token }
	if client_secret: 
		payload['client_secret'] = client_secret
	r = requests.post(TOKEN_URL, data=payload)
	data = r.json()
	assert r.status_code == 200
	assert u'error' not in data, data.get(u'error_description', data.get(u'error'))
	return data

def get_salesforce_app(request=None):
	request = request or  get_current_request()
	site_names = ('',)
	if request:  # pragma: no cover
		site_names = getattr(request, 'possible_site_names', ()) + site_names
		
	for name in site_names:
		util = component.queryUtility(sf_interfaces.ISalesforceApplication, name=name)
		if util is not None:
			return util
	return None
	
@view_config(route_name='logon.salesforce.oauth1', request_method='GET')
def salesforce_oauth1(request):
	params = request.params
	error = params.get('error')
	error_description = params.get('error_description')
	if error:
		response = hexc.HTTPBadRequest()
		response.headers.extend( sec.forget(request) )
		response.headers[b'Warning'] = error_description.encode('utf-8')
		return response

	app = get_salesforce_app()
	code = params.get('code')
	our_uri = urllib.quote(request.route_url('logon.salesforce.oauth2'))
	redir_to = '%s?grant_type=authorization_code&code=%s&client_secret=%s&client_id=%s&redirect_uri=%s' % \
				(TOKEN_URL, code, app.ClientSecret, app.ClientID, our_uri)

	return hexc.HTTPSeeOther( location=redir_to )

@view_config(route_name='logon.salesforce.oauth2', request_method='GET')
def salesforce_oauth2(request):
	params = request.params
	error = params.get('error')
	error_description = params.get('error_description')
	if error:
		response = hexc.HTTPBadRequest()
		response.headers.extend( sec.forget(request) )
		response.headers[b'Warning'] = error_description.encode('utf-8')
		return response

	response_token = dict(params)
	logger.info(response_token)

	return hexc.HTTPSeeOther( location="http://www.google.com" )
