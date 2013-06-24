# -*- coding: utf-8 -*-
"""
Salesforce user profile

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface
from zope.annotation import factory as an_factory
from zope.container import contained as zcontained

from persistent import Persistent

from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces

from nti.utils.schema import SchemaConfigured
from nti.utils.schema import createDirectFieldProperties

from . import interfaces as sf_interfaces

@interface.implementer(sf_interfaces.ISalesforceUser)
class SalesforceUser(User):
	__external_class_name__ = 'User'

	def __init__(self, username, **kwargs):
		super(SalesforceUser, self).__init__(username, **kwargs)

@component.adapter(nti_interfaces.IUser)
@interface.implementer(sf_interfaces.ISalesforceTokenInfo)
class SalesforceTokenInfo(SchemaConfigured, zcontained.Contained, Persistent):
	createDirectFieldProperties(sf_interfaces.ISalesforceTokenInfo)

	def get_response_token(self):
		result = {}
		result['access_token'] = self.AccessToken
		result['refresh_token'] = self.RefreshToken
		result['instance_url'] = self.InstanceURL
		result['id'] = self.UserID
		result['signature'] = self.Signature
		return result

_SalesforceTokenInfoFactory = an_factory(SalesforceTokenInfo)
