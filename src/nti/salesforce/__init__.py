# -*- coding: utf-8 -*-
"""
Salesforce module

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

class SalesforceException(Exception):
    pass

class InvalidSessionException(SalesforceException):
    pass
