#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.common.property import alias
from nti.common.representation import WithRepr

from nti.schema.field import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from .interfaces import IWhooshIndexSpec

@interface.implementer(IWhooshIndexSpec)
@WithRepr
class WhooshIndexSpec(SchemaConfigured):
    createDirectFieldProperties(IWhooshIndexSpec)
    
    book = alias('content')
