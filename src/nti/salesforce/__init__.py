# -*- coding: utf-8 -*-
"""
Salesforce module

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

from nti.utils.schema import SchemaConfigured
from nti.utils.schema import createDirectFieldProperties

from . import interfaces as sf_interfaces

class SalesforceException(Exception):
    pass

class InvalidSessionException(SalesforceException):
    pass

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
