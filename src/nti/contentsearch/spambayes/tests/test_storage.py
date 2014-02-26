#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_length
from hamcrest import assert_that

import os
import shutil
import unittest
import tempfile
import transaction

from nti.contentsearch.spambayes.tokenizer import tokenize
from nti.contentsearch.spambayes.storage import SQL3Classifier

from nti.contentsearch.spambayes.tests import SharedConfiguringTestLayer

class TestStorage(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	ham = """Use the param function in list context"""
	spam = """Youtube delete your video context and can only be accessed on the link posted below"""
		
	def setUp(self):
		super(TestStorage, self).setUp()
		self.path = tempfile.mkdtemp(dir="/tmp")
		self.db_path = os.path.join(self.path, "sample.db")
		
	def tearDown(self):
		super(TestStorage, self).tearDown()
		shutil.rmtree(self.path, True)
		
	def test_trainer( self ):
		sc = SQL3Classifier(self.db_path)
		transaction.begin()
		sc.learn(tokenize(self.ham), False)
		sc.learn(tokenize(self.spam), True)
		transaction.commit()
		
		rc = sc.get_record('context')
		assert_that(rc.spamcount, is_(1))
		assert_that(rc.hamcount, is_(1))
		assert_that(sc.words, has_length(17))
		
		sc2 = SQL3Classifier(self.db_path)
		assert_that(sc2.nham, is_(1))
		assert_that(sc2.nspam, is_(1))
		assert_that(sc2.words, has_length(17))
