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
from nti.tests import verifiably_provides
from nti.tests import validly_provides

from ..capability import Capability
from ..interfaces import ICapability

def test_interface():

	assert_that( Capability( None, None ), verifiably_provides( ICapability ) )
	assert_that( Capability( 'id', 'title' ), validly_provides( ICapability ) )
