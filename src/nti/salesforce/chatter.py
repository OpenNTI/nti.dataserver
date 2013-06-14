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

def get_auth_token(client_id, client_secret, security_token, username, password):
	payload = {u'client_id':client_id, u'client_secret':client_secret, 'grant_type':'password',
			   u'username':username, u'password':'%s%s' % (password, security_token) }
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
	
def create_app(client_id, client_secret, security_token):
	result = SalesforceApp(ClientID=client_id, ClientSecret=client_secret, SecurityToken=security_token)
	return result

@interface.implementer(sf_interfaces.IChatter)
class Chatter(object):

	def __init__(self, user):
		self.user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user

	@property
	def app(self):
		# We should select the application based on a given context, but for now pick the first
		utils = list(component.getUtilitiesFor(sf_interfaces.ISalesforceApplication))
		return utils[0][1] if utils else None

	@property
	def profile(self):
		return sf_interfaces.ISalesforceUserProfile(self.user)

	@property
	def userId(self):
		userId = sf_interfaces.ISalesforceUser(self.user).userId
		if not userId:
			cuser = self.get_chatter_user()
			userId = sf_interfaces.ISalesforceUser(self.user).userId = unicode(cuser['id'])
		return userId
	
	def get_chatter_user(self):
		token = self.get_auth_token()
		result = get_chatter_user(token[u'instance_url'], token[u'access_token'])
		return result

	def get_auth_token(self):
		app = self.app
		profile = self.profile
		data = get_auth_token(client_id=app.ClientID, client_secret=app.ClientSecret,
							  security_token=app.SecurityToken, username=profile.sf_username,
							  password=profile.sf_password)
		return data
