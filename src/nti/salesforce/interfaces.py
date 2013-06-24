# -*- coding: utf-8 -*-
"""
Salesforce interfaces

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

from nti.dataserver import interfaces as nti_interfaces

from nti.utils import schema as nti_schema

class ISalesforceUser(nti_interfaces.IUser):
    """
    Marker interface for a salesforce user
    """

class ISalesforceTokenInfo(interface.Interface):
    UserID = nti_schema.ValidTextLine(title='Salesforce UserID', required=False)
    AccessToken = nti_schema.ValidTextLine(title='Session ID that you can use for making Chatter API', required=True)
    RefreshToken = nti_schema.ValidTextLine(title='Token that can be used in the future to obtain new access tokens', required=True)
    InstanceURL = nti_schema.ValidTextLine(title="URL indicating the instance of the user's organization", required=True)
    Signature = nti_schema.ValidTextLine(title="Base64-encoded HMAC-SHA256", required=True)

class ISalesforceApplication(interface.Interface):
    ClientID = nti_schema.ValidTextLine(title='Client id', required=True)
    ClientSecret = nti_schema.ValidTextLine(title='Client secret', required=True)

class IChatter(interface.Interface):
    pass
