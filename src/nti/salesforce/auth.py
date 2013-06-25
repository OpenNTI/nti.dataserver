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
from pyramid import interfaces as pyramid_interfaces

from zope import interface
from zope import component
from zope.location.interfaces import ILocation

from nti.appserver import interfaces as app_interfaces

from nti.dataserver.links import Link
from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces

from . import chatter
from . import interfaces as sf_interfaces

ROUTE_NAME = u'oauth.salesforce'
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

@view_config(route_name=ROUTE_NAME, request_method='GET')
def salesforce_oauth(request):
	params = request.params
	error_response = _check_error(request, params)
	if error_response:
		return error_response

	redirect_to = params.get('state')
	if 'code' in params:
		app = chatter.get_salesforce_app(request)
		code = params['code']
		our_uri = urllib.quote(request.route_url(ROUTE_NAME))
		post_to = '%s?grant_type=authorization_code&code=%s&client_secret=%s&client_id=%s&redirect_uri=%s' % \
					(TOKEN_URL, code, app.ClientSecret, app.ClientID, our_uri)

		r = requests.post(post_to)
		params = r.json()
		error_response = _check_error(request, params)
		if error_response:
			return error_response

	response_token = params
	access_token = response_token['access_token']
	instance_url = response_token['instance_url']
	if not access_token or instance_url:
		response = hexc.HTTPBadRequest(detail="no access token found")
		return response

	# make sure we have a internal user
	user_info = chatter.get_chatter_user(instance_url, access_token)
	username = user_info['username']
	userId = user_info('id')
	user = User.get_user(username)
	if user is None:
		raise ValueError( "No user found for %s" % username )
		
	# to force a transaction commit
	request.method = 'POST'

	# save response token
	sf = sf_interfaces.ISalesforceTokenInfo(user)
	sf.UserID = userId
	sf.ID = response_token['id']
	sf.AccessToken = response_token['access_token']
	sf.RefreshToken = response_token['refresh_token']
	sf.InstanceURL = response_token['instance_url']
	sf.Signature = response_token['signature']

	if redirect_to:
		response = hexc.HTTPSeeOther(location=redirect_to)
	else:
		response = hexc.HTTPNoContent()

def link_belongs_to_user(link, user):
	link.__parent__ = user
	link.__name__ = ''
	interface.alsoProvides( link, ILocation )
	try:
		link.creator = user
		interface.alsoProvides( link, nti_interfaces.ICreated )
	except AttributeError:
		pass
	return link

@interface.implementer(app_interfaces.IAuthenticatedUserLinkProvider)
@component.adapter(nti_interfaces.IUser, pyramid_interfaces.IRequest)
class SalesforceLinkProvider(object):

	rel = ROUTE_NAME
	
	def __init__( self, user, request):
		self.user = user
		self.request = request

	def get_links( self ):
		app = chatter.get_salesforce_app(self.request)
		sf = sf_interfaces.ISalesforceTokenInfo(self.user, None)
		if app and sf and not sf.RefreshToken:
			our_uri = urllib.quote(self.request.route_url(ROUTE_NAME))
			url = '%s?response_type=code&client_id=%s&redirect_uri=%s' % (AUTHORIZE_URL, app.ClientID, our_uri)
			link = Link(target=url, rel=self.rel, method='GET', title='Salesforce OAuth')
			return (link,)
		else:
			return ()
