#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_key
from hamcrest import has_entry

import nti.tests
from nti.tests import verifiably_provides, validly_provides

from ..interfaces import INotificationPayload
from ..payload import APNSPayload

def test_payload_provides():

	payload = APNSPayload()
	assert_that( payload, verifiably_provides( INotificationPayload ) )

	payload.alert = "alert"
	assert_that( payload, validly_provides( INotificationPayload ) )
