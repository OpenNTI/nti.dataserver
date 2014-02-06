#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import none
from hamcrest import is_not
from hamcrest import assert_that

import stripe

from ...tests import create_user
from ...tests import create_purchase
from ...tests import create_random_user
from ...tests import ConfiguringTestBase
from ...tests import create_purchase_attempt
from ...tests import create_and_register_purchase_attempt

TEST_WITH_STRIPE = True

class TestBaseProcessorMixin(object):

    book_id = 'xyz-book'

    @classmethod
    def setUpClass(cls):
        super(TestBaseProcessorMixin, cls).setUpClass()
        cls.api_key = stripe.api_key
        stripe.api_key = u'sk_test_3K9VJFyfj0oGIMi7Aeg3HNBp'

    @classmethod
    def tearDownClass(cls):
        super(TestBaseProcessorMixin, cls).tearDownClass()
        stripe.api_key = cls.api_key

