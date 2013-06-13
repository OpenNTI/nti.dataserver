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
from zope.annotation import factory as an_factory

from nti.dataserver.users import user_profile
from nti.dataserver import interfaces as nti_interfaces

from . import interfaces as sf_interfaces

VERSION = u'v27.0'
TOKEN_URL = u'https://na1.salesforce.com/services/oauth2/token'

def get_auth_token(client_id, client_secret, security_token, username, password):
	payload = {u'client_id':client_id, u'client_secret':client_secret, 'grant_type':'password',
			   u'username':username, u'password':'%s%s' % (password, security_token) }
	r = requests.post(TOKEN_URL, data=payload)
	data = r.json()
	assert r.status_int == 200
	assert u'error' not in data, data.get(u'error_description', data.get(u'error'))
	return data


@interface.implementer(sf_interfaces.IChatter)
class Chatter(object):

	_v_access_token = None
	_v_instance_url = None

	access_token = property(lambda s: s._v_access_token, lambda s, x: setattr(s ,'_v_access_token',x))
	instance_url = property(lambda s: s._v_instance_url, lambda s, x: setattr(s , '_v_instance_url', x))


@component.adapter(sf_interfaces.ISalesforceUser)
@interface.implementer(sf_interfaces.ISalesforceUserProfile)
class SalesforceUserProfile(user_profile.EmailRequiredUserProfile):
	
	_sf_username = None
	_sf_password = None
	
	@property
	def context(self):
		return self.__parent__
	
	def get_sf_username(self):
		result = self.context.username if not self._sf_username else self._sf_username
		return result
	sf_username = property(get_sf_username, lambda s, x: setattr(s, '_sf_username', x))
	
	def get_sf_password(self):
		result = self.context.password if not self._sf_password else self._sf_password
		return result
	sf_password = property(get_sf_password, lambda s, x: setattr(s, '_sf_password', x))

@component.adapter(nti_interfaces.IUser)
@interface.implementer(sf_interfaces.ISalesforceUser)
class SalesforceUser(object):
	pass


_SalesforceUserFactory = an_factory(SalesforceUser)
