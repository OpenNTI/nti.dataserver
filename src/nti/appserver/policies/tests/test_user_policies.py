#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import PyPDF2 as pyPdf

from .. import user_policies

from nti.appserver.tests.test_application import SharedApplicationTestBase

from hamcrest import (assert_that, is_)

class TestUserPolicies(SharedApplicationTestBase):

	pass
