#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import math
import time
from datetime import datetime

def get_datetime(x=None):
    x = x or time.time()
    return datetime.fromtimestamp(float(x))

def date_to_videotimestamp(dt):
    dt = float(dt) if isinstance(dt, six.string_types) else dt
    dt = get_datetime(dt) if isinstance(dt, (float, long)) else dt
    if isinstance(dt, datetime):
        milli = math.floor(dt.microsecond / 1000.0)
        result = u"%02d:%02d:%02d.%03d" % (dt.hour, dt.minute, dt.second, milli)
        return result
    return u''

def videotimestamp_to_datetime(qstring):
    # this method parses a timestamp of the form hh:mm::ss.uuu
    qstring = qstring.replace(" ", "")
    year = month = day = 1
    hour = minute = second = microsecond = 0
    if len(qstring) >= 2:
        hour = int(qstring[0:2])
    if len(qstring) >= 5:
        minute = int(qstring[3:5])
    if len(qstring) >= 8:
        second = int(qstring[6:8])
    if len(qstring) == 12:
        microsecond = int(qstring[9:12]) * 1000
    if len(qstring) == 13:
        microsecond = int(qstring[9:13])

    result = datetime(year=year, month=month, day=day, hour=hour,
                      minute=minute, second=second, microsecond=microsecond)
    return result
mediatimestamp_to_datetime = videotimestamp_to_datetime

def video_date_to_millis(dt):
    start = datetime(year=1, month=1, day=1)
    diff = dt - start
    return diff.total_seconds() * 1000.0

