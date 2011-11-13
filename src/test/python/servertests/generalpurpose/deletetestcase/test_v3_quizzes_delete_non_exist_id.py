'''
Created on Oct 18, 2011

@author: ltesti
'''

from servertests.generalpurpose import V3Constants_Quizzes
from servertests.generalpurpose.deletetestcase import DeleteTests
from servertests.generalpurpose.utilities.catagory import ServerTestV3_quizzes

class V3_QuizzesServer404NonExistIDGetTestCase(DeleteTests):

	def __init__(self, *args, **kwargs):
		self.constants_object = V3Constants_Quizzes()
		super(V3_QuizzesServer404NonExistIDGetTestCase, self).__init__(ServerTestV3_quizzes, self.constants_object, *args, **kwargs)

	def test_Server404NonExistIDGetTestCase(self):
		self.notFoundDeleteTest(url=self.constants_object.URL_NONEXIST_ID)
	
if __name__ == '__main__':
	import unittest
	unittest.main()
