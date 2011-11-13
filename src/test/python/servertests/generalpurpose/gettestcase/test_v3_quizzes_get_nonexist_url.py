'''
Created on Oct 4, 2011

@author: ltesti
'''

from servertests.generalpurpose import V3Constants_Quizzes
from servertests.generalpurpose.gettestcase import GetTests
from servertests.generalpurpose.utilities.catagory import ServerTestV3_quizzes

class V3QuizzesServer404NonExistantURLGetTestCase(GetTests):

	def __init__(self, *args, **kwargs):
		self.constants_object = V3Constants_Quizzes()
		super(V3QuizzesServer404NonExistantURLGetTestCase, self).__init__(ServerTestV3_quizzes, self.constants_object, *args, **kwargs)

	def test_Server404NonExistantURLGetTestCase(self):
		self.notFoundGetTest(url=self.constants_object.URL_NONEXIST_ID)
	
if __name__ == '__main__':
	import unittest
	unittest.main()