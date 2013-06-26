# -*- coding: utf-8 -*-
"""
Salesforce interfaces

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

from nti.utils import schema as nti_schema

class ISalesforceTokenInfo(interface.Interface):
    ID = nti_schema.ValidTextLine(title='Identity URL', required=False)
    UserID = nti_schema.ValidTextLine(title='User ID', required=True)
    AccessToken = nti_schema.ValidTextLine(title='Session ID that you can use for making Chatter API', required=False)
    RefreshToken = nti_schema.ValidTextLine(title='Token that can be used in the future to obtain new access tokens', required=True)
    InstanceURL = nti_schema.ValidTextLine(title="URL indicating the instance of the user's organization", required=True)
    Signature = nti_schema.ValidTextLine(title="Base64-encoded HMAC-SHA256", required=False)

    def can_chatter():
        pass

    def response_token():
        pass

class ISalesforceApplication(interface.Interface):
    ClientID = nti_schema.ValidTextLine(title='Client id', required=True)
    ClientSecret = nti_schema.ValidTextLine(title='Client secret', required=True)

class IChatter(interface.Interface):
    pass
