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

from nti.store.tests import SharedConfiguringTestLayer

from nti.store.payments.stripe.tests import create_user
from nti.store.payments.stripe.tests import create_purchase
from nti.store.payments.stripe.tests import create_random_user
from nti.store.payments.stripe.tests import create_purchase_attempt
from nti.store.payments.stripe.tests import create_and_register_purchase_attempt

from nti.testing.layers import find_test

TEST_WITH_STRIPE = True

class StripeProcessorTestLayer(SharedConfiguringTestLayer):

    @classmethod
    def setUp(cls):
        cls.api_key = stripe.api_key
        stripe.api_key = u'sk_test_3K9VJFyfj0oGIMi7Aeg3HNBp'

    @classmethod
    def testSetUp(cls, test=None):
        cls.test = test or find_test()
        cls.test.book_id = 'xyz-book'

    @classmethod
    def tearDown(cls):
        stripe.api_key = cls.api_key
