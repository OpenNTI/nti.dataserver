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

from nti.apns import interfaces

def test_feedback_event():
	event = interfaces.APNSDeviceFeedback(0, b'b' * 32)
	assert_that( event, validly_provides(interfaces.IDeviceFeedbackEvent) )
	assert_that( event, verifiably_provides(interfaces.IDeviceFeedbackEvent) )

	repr(event)
