'''
Created on Oct 10, 2011

@author: ltesti
'''

from servertests.generalpurpose import V3Constants_Results
from servertests.generalpurpose.posttestcase import PostTests
from servertests.generalpurpose.utilities.catagory import ServerTestV3_results
from servertests.generalpurpose.utilities.body_data_extracter import URL_Fail_Post_Assessment

class V3_ResultsServer401JsonFormatIncorrectPasswordPostTestCase(PostTests):

	def __init__(self, *args, **kwargs):
		self.constants_object = V3Constants_Results()
		super(V3_ResultsServer401JsonFormatIncorrectPasswordPostTestCase, self).__init__(ServerTestV3_results, self.constants_object, *args, **kwargs)

	def test_Server401JsonFormatIncorrectPasswordPostTestCase(self):
		self.unauthorizedPostTestJsonFormat(password=self.constants_object.incorrectPassword, bodyDataExtracter=URL_Fail_Post_Assessment())
	
if __name__ == '__main__':
	import unittest
	unittest.main()