#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import six
import pytz

import simplejson as json

from datetime import timedelta

from pyramid.interfaces import IRequest

from pytz.exceptions import UnknownTimeZoneError

from six.moves.urllib_parse import unquote

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from nti.appserver.interfaces import IDisplayableTimeProvider

from nti.coremetadata.interfaces import IUser

logger = __import__('logging').getLogger(__name__)

TIMEZONE_COOKIE = 'timezone'
TIMEZONE_ID_HEADER = 'X-NTI-Client-Timezone'
TIMEZONE_OFFSET_HEADER = 'X-NTI-Client-TZOffset'


@component.adapter(IUser, IRequest)
@interface.implementer(IDisplayableTimeProvider)
class DisplayableTimeProvider(object):

    DEFAULT_TIMEZONE_STR = 'UTC'

    def __init__(self, user, request):
        self.user = user
        self.request = request

    @Lazy
    def timezone_cookie_dict(self):
        result = self.request.cookies.get(TIMEZONE_COOKIE)
        if result and isinstance(result, six.string_types):
            result = unquote(result)
            try:
                result = json.loads(result)
            except ValueError:
                result = None
        return result or {}

    @Lazy
    def timezone_name_cookie(self):
        return self.timezone_cookie_dict.get('name')

    @Lazy
    def timezone_offset_cookie(self):
        return self.timezone_cookie_dict.get('offset')

    @Lazy
    def _timezone_identifier(self):
        return self.timezone_name_cookie \
            or self.request.headers.get(TIMEZONE_ID_HEADER)

    @Lazy
    def _timezone_offset(self):
        # The timezone offset in +/- minutes.
        val =  self.timezone_offset_cookie \
            or self.request.headers.get(TIMEZONE_OFFSET_HEADER)
        if val is not None:
            try:
                result = int(val)
            except (TypeError, ValueError):
                logger.warn('Invalid provided timezone offset (%s)', val)
                result = None
            return result

    @Lazy
    def _timezone_offset_delta(self):
        if self._timezone_offset:
            return timedelta(minutes=self._timezone_offset)

    @Lazy
    def _default_timezone(self):
        """
        Return the timezone obj for our timezone_str.
        """
        return pytz.timezone(self.DEFAULT_TIMEZONE_STR)

    @Lazy
    def _timezone(self):
        """
        Return the timezone obj for our timezone_str.
        """
        if self._timezone_identifier:
            try:
                return pytz.timezone(self._timezone_identifier)
            except UnknownTimeZoneError:
                logger.warn('Unknown timezone %s', self._timezone_identifier)

    @Lazy
    def _timezone_display(self):
        if self._timezone:
            result = self._timezone.zone
        elif self._timezone_offset:
            hours = self._timezone_offset / 60
            result = 'GMT%+.0f' % hours
        else:
            result = self._default_timezone.zone
        return result

    def get_timezone_display_name(self):
        return self._timezone_display

    def adjust_date(self, date):
        if self._timezone:
            utc_date = pytz.utc.localize(date)
            result = utc_date.astimezone(self._timezone)
        elif self._timezone_offset_delta:
            result = date + self._timezone_offset_delta
        else:
            utc_date = pytz.utc.localize(date)
            result = utc_date.astimezone(self._default_timezone)
        return result
