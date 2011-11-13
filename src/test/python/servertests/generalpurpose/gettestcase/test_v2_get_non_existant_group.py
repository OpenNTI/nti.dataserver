'''
Created on Oct 4, 2011

@author: ltesti
'''

from servertests.generalpurpose import V2Constants
from servertests.generalpurpose.gettestcase import GetTests
from servertests.generalpurpose.utilities.catagory import ServerTestV2

class V2Server404NonExistantGroupGetTestCase(GetTests):

	def __init__(self, *args, **kwargs):
		self.constants_object = V2Constants()
		super(V2Server404NonExistantGroupGetTestCase, self).__init__(ServerTestV2, self.constants_object, *args, **kwargs)

	def test_Server404NonExistantGroupGetTestCase(self):
		self.notFoundGetTest(url=self.constants_object.URL_USER_NONEXIST_GROUP)
	
if __name__ == '__main__':
	import unittest
	unittest.main()