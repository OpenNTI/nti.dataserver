#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Store module

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

import zope.i18nmessageid
MessageFactory = zope.i18nmessageid.MessageFactory('nti.dataserver')

from zope import interface

from . import interfaces as store_interfaces

@interface.implementer(store_interfaces.INTIStoreException)
class NTIStoreException(Exception):
    pass

class InvalidPurchasable(NTIStoreException):
    pass

class PricingException(NTIStoreException):
    pass

