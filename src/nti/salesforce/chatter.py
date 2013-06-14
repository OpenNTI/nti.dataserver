# -*- coding: utf-8 -*-
"""
Chatter commands

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import requests

from zope import component
from zope import interface

from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces

from nti.utils.schema import SchemaConfigured
from nti.utils.schema import createDirectFieldProperties

from . import interfaces as sf_interfaces

VERSION = u'v27.0'
TOKEN_URL = u'https://na1.salesforce.com/services/oauth2/token'

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
	payload = {u'client_id':client_id, 'grant_type':'password', u'username':refresh_token }
	if client_secret:
		payload['client_secret'] = client_secret
	r = requests.post(TOKEN_URL, data=payload)
	data = r.json()
	assert r.status_code == 200
	assert u'error' not in data, data.get(u'error_description', data.get(u'error'))
	return data

def get_chatter_user(instance_url, access_token, version=VERSION):
	url = '%s/services/data/%s/chatter/users/me' % (instance_url, version)
	headers = {u'Authorization': u'Bearer %s' % access_token}
	r = requests.get(url, headers=headers)
	assert r.status_code == 200
	data = r.json()
	assert u'error' not in data, data.get(u'error_description', data.get(u'error'))
	return data

@interface.implementer(sf_interfaces.ISalesforceApplication)
class SalesforceApp(SchemaConfigured):
	
	# create all interface fields
	createDirectFieldProperties(sf_interfaces.ISalesforceApplication)
	
	def ConsumerKey(self):
		return self.ClientID
		
	def ConsumerSecret(self):
		return self.ClientSecret
	
def create_app(client_id, client_secret):
	result = SalesforceApp(ClientID=client_id, ClientSecret=client_secret)
	return result

@interface.implementer(sf_interfaces.IChatter)
class Chatter(object):

	def __init__(self, user, response_token, refresh_token=None):
		self.response_token = response_token
		self.refresh_token = refresh_token or response_token.get('refresh_token')
		self.user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user

	@property
	def application(self):
		# We should select the application based on a given context, but for now pick the first
		utils = list(component.getUtilitiesFor(sf_interfaces.ISalesforceApplication))
		return utils[0][1] if utils else None

	@property
	def userId(self):
		userId = sf_interfaces.ISalesforceUser(self.user).userId
		if not userId:
			cuser = self.get_chatter_user()
			userId = sf_interfaces.ISalesforceUser(self.user).userId = unicode(cuser['id'])
		return userId
	
	def get_chatter_user(self):
		token = self.response_token
		result = get_chatter_user(token[u'instance_url'], token[u'access_token'])
		return result

	def new_response_token(self):
		if self.refresh_token:
			application = self.application
			self.response_token = refresh_token(client_id=application.ClientID, refresh_token=self.refresh_token)
			return self.response_token
		return None
