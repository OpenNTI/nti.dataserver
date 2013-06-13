# -*- coding: utf-8 -*-
"""
Salesforce interfaces

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema
from zope import interface

from nti.dataserver.users.user_profile import interfaces as profile_interfaces

from nti.utils import schema as nti_schema

class ISalesforceUserProfile(profile_interfaces.IEmailRequiredUserProfile):
    sf_username = nti_schema.ValidTextLine(title='Salesforce Username', required=False)
    sf_password = nti_schema.ValidTextLine(title='SalesForce User Password', required=False)

class ISalesforceApplication(interface.Interface):
    ClientID = nti_schema.ValidTextLine(title='Client id', required=True)
    ClientSecret = nti_schema.ValidTextLine(title='Client secret', required=True)
    SecurityToken = nti_schema.ValidTextLine(title='Security token', required=True)

class ISalesforceUser(interface.interface):
    pass

class IChatter(ISalesforceUser):
    pass
