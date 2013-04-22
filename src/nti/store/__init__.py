# -*- coding: utf-8 -*-
"""
Store module

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import zope.i18nmessageid
MessageFactory = zope.i18nmessageid.MessageFactory('nti.dataserver')

from .utils import *

class StoreException(Exception):
    pass

class InvalidPurchasable(StoreException):
    pass

class PricingException(StoreException):
    pass
