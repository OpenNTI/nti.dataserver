'''
Created on Oct 4, 2011

@author: ltesti
'''

from servertests.generalpurpose import V3Constants_Results
from servertests.generalpurpose.gettestcase import GetTests
from servertests.generalpurpose.utilities.catagory import ServerTestV3_results
from servertests.generalpurpose.utilities.body_data_extracter import URL_DefaultV3_Post

class V3ResultsServer200GetGroupGetTestCase(GetTests):

	def __init__(self, *args, **kwargs):
		self.constants_object = V3Constants_Results()
		super(V3ResultsServer200GetGroupGetTestCase, self).__init__(ServerTestV3_results, self.constants_object, *args, **kwargs)

	def test_Server200GetGroupGetTestCase(self):
		self.okGetTest(url=self.constants_object.URL_USER_POST, bodyDataExtracter=URL_DefaultV3_Post())
	
if __name__ == '__main__':
	import unittest
	unittest.main()