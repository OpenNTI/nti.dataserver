#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import unittest
from hamcrest import assert_that
from hamcrest import is_
from nti.testing.matchers import validly_provides

from ..who_classifiers import application_request_classifier as _nti_request_classifier
from ..who_classifiers import CLASS_BROWSER_APP
from repoze.who.interfaces import IRequestClassifier

class TestClassifier(unittest.TestCase):

	def test_request_classifier(self):

		assert_that( _nti_request_classifier, validly_provides(IRequestClassifier) )

		# The default
		environ = {}
		environ['REQUEST_METHOD'] = 'GET'

		assert_that( _nti_request_classifier( environ ), is_( 'browser' ) )

		# XHR
		environ['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'
		assert_that( _nti_request_classifier( environ ),
					 is_( CLASS_BROWSER_APP ) )
		environ['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'.upper() # case-insensitive
		assert_that( _nti_request_classifier( environ ),
					 is_( CLASS_BROWSER_APP ) )

		del environ['HTTP_X_REQUESTED_WITH']

		environ['HTTP_REFERER'] = 'http://foo'

		# A referrer alone isn't enough
		assert_that( _nti_request_classifier( environ ), is_( 'browser' ) )

		# Add  a user agent
		environ['HTTP_USER_AGENT'] = 'Mozilla'
		__traceback_info__ = environ
		assert_that( _nti_request_classifier( environ ), is_( CLASS_BROWSER_APP ) )

		# But a default accept changes back to browser
		environ['HTTP_ACCEPT'] = '*/*'
		assert_that( _nti_request_classifier( environ ), is_( 'browser' ) )

		environ['HTTP_ACCEPT'] = 'text/plain'
		assert_that( _nti_request_classifier( environ ), is_( CLASS_BROWSER_APP ) )

		environ['HTTP_ACCEPT'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
		assert_that( _nti_request_classifier( environ ), is_( 'browser' ) )

		# Temporary hack for old iPad apps
		environ['HTTP_USER_AGENT'] = "NTIFoundation DataLoader NextThought/1.0.2/34053 (x86_64; 7.0.3)"
		assert_that( _nti_request_classifier( environ ), is_( CLASS_BROWSER_APP ) )

		environ['HTTP_USER_AGENT'] = "NextThought/1.0.2 CFNetwork/672.0.8 Darwin/13.0.0"
		assert_that( _nti_request_classifier( environ ), is_( CLASS_BROWSER_APP ) )

		del environ['HTTP_REFERER']
		environ['HTTP_USER_AGENT'] = "NTIFoundation DataLoader NextThought/1.0.2/34053 (x86_64; 7.0.3)"
		assert_that( _nti_request_classifier( environ ), is_( CLASS_BROWSER_APP ) )

		environ['HTTP_USER_AGENT'] = "NextThought/1.0.2 CFNetwork/672.0.8 Darwin/13.0.0"
		assert_that( _nti_request_classifier( environ ), is_( CLASS_BROWSER_APP ) )
