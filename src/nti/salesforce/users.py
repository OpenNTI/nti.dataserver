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

from nti.dataserver.users import user_profile
from nti.dataserver import interfaces as nti_interfaces

from nti.utils.schema import SchemaConfigured
from nti.utils.schema import createDirectFieldProperties

from . import interfaces as sf_interfaces

@component.adapter(nti_interfaces.IUser)
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

user_profile.add_profile_fields(sf_interfaces.ISalesforceUserProfile, SalesforceUserProfile)
_SalesforceUserProfileFactory = an_factory(SalesforceUserProfile)

@component.adapter(nti_interfaces.IUser)
@interface.implementer(sf_interfaces.ISalesforceUser)
class SalesforceUser(SchemaConfigured, zcontained.Contained, Persistent):
	createDirectFieldProperties(sf_interfaces.ISalesforceUser)

_SalesforceUserFactory = an_factory(SalesforceUser)
