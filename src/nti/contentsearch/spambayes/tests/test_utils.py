#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import greater_than_or_equal_to

import os
import shutil
import tempfile
import unittest

from nti.contentsearch.spambayes.tokenizer import tokenize
from nti.contentsearch.spambayes.utils.emessage import create_sql3classifier_db

from nti.contentsearch.spambayes.tests import SharedConfiguringTestLayer

class TestUtils(unittest.TestCase):

	layer = SharedConfiguringTestLayer
	
	def setUp(self):
		super(TestUtils, self).setUp()
		self.path = tempfile.mkdtemp(dir="/tmp")
		self.dbpath = os.path.join(self.path, "sample.db")
		
	def tearDown(self):
		super(TestUtils, self).tearDown()
		shutil.rmtree(self.path, True)
		
	def test_create_sql3classifier_db( self ):
		directory = os.path.dirname(__file__)
		sc = create_sql3classifier_db(self.dbpath, directory, fnfilter='_spam*')
		assert_that(sc.words, has_length(858))
		rc = sc.get_record('and')
		assert_that(rc.spamcount, is_(3))
		
		text = 'You Will Sell A Product Which Costs Nothing'
		prob = sc.spamprob(tokenize(text), False)
		assert_that(prob, greater_than_or_equal_to(0.99))
