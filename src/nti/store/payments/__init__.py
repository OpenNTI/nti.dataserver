#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

FAILED = u'Failed'
PENDING = u'Pending'
SUCCESS = u'Success'
CANCELLED = 'Cancelled'

status_codes = (u'Reserved', u'Reserved', SUCCESS, u'Failure', FAILED,
                PENDING, CANCELLED)
