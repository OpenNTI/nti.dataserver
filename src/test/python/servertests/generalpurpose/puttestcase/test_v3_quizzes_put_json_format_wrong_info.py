'''
Created on Oct 10, 2011

@author: ltesti
'''

from servertests.generalpurpose import V3Constants_Quizzes
from servertests.generalpurpose.puttestcase import PutTests
from servertests.generalpurpose.utilities.catagory import ServerTestV3_quizzes

class V3_QuizzesServer500JsonFormatWrongInfoPutTestCase(PutTests):

	def __init__(self, *args, **kwargs):
		self.constants_object = V3Constants_Quizzes()
		super(V3_QuizzesServer500JsonFormatWrongInfoPutTestCase, self).__init__(ServerTestV3_quizzes, self.constants_object, *args, **kwargs)

	def test_Server500JsonFormatWrongInfoPutTestCase(self):
		self.wrongTypePutTestJsonFormat(data=self.constants_object.WRONG_INFO)
	
if __name__ == '__main__':
	import unittest
	unittest.main()