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

from zope import component

from nti.contentfragments.interfaces import IPlainTextContentFragment

from nti.contentprocessing import tokenize_content

def sanitize_content(text, table=None, tokens=False, lang='en'):
    """
    clean any html from the specified text and then tokenize it

    :param text: context to sanitize
    :param tokens: boolean to return a list of tokens
    :param table: translation table
    """
    if not text:
        return text

    # turn incoming into plain text.
    # NOTE: If the HTML included entities like like &lt,
    # this may still have things in it that sort of look like
    # tags:
    #    &lt;link text&gt; => <link text>
    # But of course we CANNOT and MUST NOT attempt to run an additional
    # parsing pass on it, as that's likely to wind up with gibberish results
    # since its nothing actually close to HTML
    # Since we're using a named adapter, we need to be careful
    # not to re-adapt multiple times
    raw = text
    text = component.getAdapter(text, IPlainTextContentFragment, name='text')
    __traceback_info__ = raw, text, type(text)

    # translate and tokenize words
    text = text.translate(table) if table else text
    tokenized_words = tokenize_content(text, lang)
    result = tokenized_words if tokens else ' '.join(tokenized_words)
    return result

## date/time functions

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
