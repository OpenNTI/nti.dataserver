import os
import shutil
import unittest
import tempfile
import transaction

from zope import interface
from persistent import Persistent
from zope.annotation.interfaces import IAttributeAnnotatable

from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch.spambayes.tokenizer import tokenize
from nti.contentsearch.spambayes.storage import SQL3Classifier
from nti.contentsearch.spambayes.storage import PersistentClassifier
from nti.contentsearch.spambayes.interfaces import IObjectClassifierMetaData

from nti.contentsearch.spambayes.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_, has_length)

@interface.implementer(nti_interfaces.IModeledContent, IAttributeAnnotatable)
class Foo(Persistent):
	pass

class TestStorage(ConfiguringTestBase):

	ham = """Use the param function in list context"""
	spam = """Youtube delete your video context and can only be accessed on the link posted below"""
		
	def setUp(self):
		super(TestStorage, self).setUp()
		self.path = tempfile.mkdtemp(dir="/tmp")
		self.db_path = os.path.join(self.path, "sample.db")
		
	def tearDown(self):
		super(TestStorage, self).tearDown()
		shutil.rmtree(self.path, True)
		
	def xtest_trainer( self ):
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

	def test_persistent_classifier(self):
		pc = PersistentClassifier()
		foo = Foo()
		pc.mark_spam(foo)
		a = IObjectClassifierMetaData(foo, None)
		assert_that(a.is_spam, is_(True))
		
if __name__ == '__main__':
	unittest.main()
