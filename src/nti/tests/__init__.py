#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Helpers for testing.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import zope.deferredimport
zope.deferredimport.initialize()

zope.deferredimport.deprecated(
	"Import from nti.testing or nti.app.testing submodules instead",
	time_monotonically_increases = 'nti.testing.time:time_monotonically_increases',
	is_true = 'nti.testing.matchers:is_true',
	is_false = 'nti.testing.matchers:is_false',
	is_empty = 'nti.testing.matchers:is_empty',
	has_attr = 'nti.testing.matchers:has_attr',
	provides = 'nti.testing.matchers:provides',
	verifiably_provides = 'nti.testing.matchers:verifiably_provides',
	validly_provides = 'nti.testing.matchers:validly_provides',
	implements = 'nti.testing.matchers:implements',
	validated_by = 'nti.testing.matchers:validated_by',
	aq_inContextOf = 'nti.testing.matchers:aq_inContextOf',
	not_validated_by = 'nti.testing.matchers:not_validated_by',
	AbstractTestBase = 'nti.testing.base:AbstractTestBase',
	AbstractSharedTestBase = 'nti.testing.base:AbstractSharedTestBase',
	ConfiguringTestBase = 'nti.testing.base:ConfiguringTestBase',
	SharedConfiguringTestBase = 'nti.testing.base:SharedConfiguringTestBase',
	module_setup = 'nti.testing.base:module_setup',
	module_teardown = 'nti.testing.base:module_teardown',
	TypeCheckedDict = 'nti.testing.matchers:TypeCheckedDict',
	ByteHeadersResponse = 'nti.app.testing.request_response:ByteHeadersResponse',
	ByteHeadersDummyRequest = 'nti.app.testing.request_response:ByteHeadersDummyRequest' )

# In order for deferred import to work, we have
# to define something of our own. This seems to be a bug
_foo = 1
