#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from datetime import datetime

from zope.schema.interfaces import InvalidValue

from nti.schema.field import ValidTextLine

class Duration(ValidTextLine):
     
    def _validate(self, value):
        if value:
            try:
                d_number, d_kind = value.split() 
                datetime.timedelta(**{d_kind.lower():int(d_number)})
            except Exception:
                raise InvalidValue('Invalid duration', value, self.__name__)     
        super(Duration, self)._validate(value)
