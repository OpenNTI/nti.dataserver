#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import isodate
from datetime import datetime

from zope import interface
from zope.schema.interfaces import IFromUnicode
from zope.schema.interfaces import InvalidValue

from nti.schema.field import ValidTextLine
from nti.schema.field import DateTime as _DateTime

class Duration(ValidTextLine):
     
    def _validate(self, value):
        if value:
            try:
                d_number, d_kind = value.split() 
                datetime.timedelta(**{d_kind.lower():int(d_number)})
            except Exception:
                raise InvalidValue('Invalid duration', value, self.__name__)     
        super(Duration, self)._validate(value)

@interface.implementer(IFromUnicode)
class DateTime(_DateTime):
    
    def fromUnicode(self, s):
        try:
            result = isodate.parse_datetime(s)
        except Exception:
            raise InvalidValue('Invalid datetime', s, self.__name__)  
        self.validate(result)
        return result
