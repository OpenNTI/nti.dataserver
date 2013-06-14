# -*- coding: utf-8 -*-
"""
Salesforce interfaces

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

from nti.utils import schema as nti_schema

class ISalesforceUser(interface.Interface):
    userId = nti_schema.ValidTextLine(title='Salesforce userID', required=True)

class ISalesforceApplication(interface.Interface):
    ClientID = nti_schema.ValidTextLine(title='Client id', required=True)
    ClientSecret = nti_schema.ValidTextLine(title='Client secret', required=True)

class IChatter(interface.Interface):
    pass
