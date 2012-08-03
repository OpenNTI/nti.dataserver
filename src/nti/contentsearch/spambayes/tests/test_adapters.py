import unittest

from zope import interface
from persistent import Persistent
from zope.annotation.interfaces import IAttributeAnnotatable

from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch.spambayes import PERSISTENT_SPAM_INT

from nti.contentsearch.spambayes.storage import Trainer
from nti.contentsearch.spambayes.interfaces import IUserSpamClassifier
from nti.contentsearch.spambayes.interfaces import IObjectClassifierMetaData

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.contentsearch.spambayes.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_)

@interface.implementer(nti_interfaces.IModeledContent, IAttributeAnnotatable)
class Foo(Persistent):
	pass

class TestAdapters(ConfiguringTestBase):

	def test_classifier_metadata(self):
		foo = Foo()
		pc = Trainer()
		pc.mark_spam(foo)
		a = IObjectClassifierMetaData(foo, None)
		assert_that(a.spam_classification, is_(PERSISTENT_SPAM_INT))
		
	@WithMockDSTrans
	def test_user_classifer(self):
		usr = User.create_user( mock_dataserver.current_mock_ds, username='nt@nti.com', password='temp' )
		usp = IUserSpamClassifier(usr, None)
		usp.train(u'test string', True)
		usp.train(u'another text', True)
		usp.untrain(u'test string', True)
		usp.classify('another text')
		
if __name__ == '__main__':
	unittest.main()
