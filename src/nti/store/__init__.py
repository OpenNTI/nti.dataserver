#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Store module

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import zope.i18nmessageid
MessageFactory = zope.i18nmessageid.MessageFactory('nti.dataserver')

from zope import interface

from pyramid.threadlocal import get_current_request

from .utils import *
from . import interfaces as store_interfaces

@interface.implementer(store_interfaces.INTIStoreException)
class NTIStoreException(Exception):
    pass

class InvalidPurchasable(NTIStoreException):
    pass

class PricingException(NTIStoreException):
    pass

def get_possible_site_names(request=None, include_default=False):
    request = request or get_current_request()
    if not request:
        return () if not include_default else ('',)
    __traceback_info__ = request

    site_names = getattr(request, 'possible_site_names', ())
    if include_default:
        site_names += ('',)
    return site_names
