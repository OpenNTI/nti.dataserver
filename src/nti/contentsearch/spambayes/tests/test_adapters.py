import unittest

from zope import interface
from persistent import Persistent
from zope.annotation.interfaces import IAttributeAnnotatable

from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch.spambayes.interfaces import ISpamClassifier

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.contentsearch.spambayes.tests import ConfiguringTestBase


@interface.implementer(nti_interfaces.IModeledContent, IAttributeAnnotatable)
class Foo(Persistent):
	pass

class TestAdapters(ConfiguringTestBase):
		
	@WithMockDSTrans
	def test_user_classifer(self):
		usr = User.create_user( mock_dataserver.current_mock_ds, username='nt@nti.com', password='temp' )
		usp = ISpamClassifier(usr, None)
		usp.train(u'test string', True)
		usp.train(u'another text', True)
		usp.untrain(u'test string', True)
		usp.classify('another text')
		
if __name__ == '__main__':
	unittest.main()
