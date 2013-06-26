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

from nti.dataserver import interfaces as nti_interfaces

from nti.utils.schema import SchemaConfigured
from nti.utils.schema import createDirectFieldProperties

from . import interfaces as sf_interfaces

@component.adapter(nti_interfaces.IUser)
@interface.implementer(sf_interfaces.ISalesforceTokenInfo)
class SalesforceTokenInfo(SchemaConfigured, zcontained.Contained, Persistent):
	createDirectFieldProperties(sf_interfaces.ISalesforceTokenInfo)

	def can_chatter(self):
		return self.RefreshToken is not None and self.UserID is not None and self.InstanceURL

	def response_token(self):
		result = {}
		result['id'] = self.ID
		result['signature'] = self.Signature
		result['instance_url'] = self.InstanceURL
		result['access_token'] = self.AccessToken
		result['refresh_token'] = self.RefreshToken
		return result

_SalesforceTokenInfoFactory = an_factory(SalesforceTokenInfo)
