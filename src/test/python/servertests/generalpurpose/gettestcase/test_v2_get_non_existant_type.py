'''
Created on Oct 4, 2011

@author: ltesti
'''

from servertests.generalpurpose import V2Constants
from servertests.generalpurpose.gettestcase import GetTests
from servertests.generalpurpose.utilities.catagory import ServerTestV2

class V2Server200NonExistantTypeGetTestCase(GetTests):

	def __init__(self, *args, **kwargs):
		self.constants_object = V2Constants()
		super(V2Server200NonExistantTypeGetTestCase, self).__init__(ServerTestV2, self.constants_object, *args, **kwargs)

	def test_Server200NonExistantTypeGetTestCase(self):
		self.okGetTest(url=self.constants_object.URL_USER_NONEXIST_TYPE)
	
if __name__ == '__main__':
	import unittest
	unittest.main()