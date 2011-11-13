'''
Created on Oct 18, 2011

@author: ltesti
'''

from servertests.generalpurpose import V3Constants_Results
from servertests.generalpurpose.deletetestcase import DeleteTests
from servertests.generalpurpose.utilities.catagory import ServerTestV3_results
from servertests.generalpurpose.utilities.body_data_extracter import URL_Delete_Group

class V3_ResultsServer405DeleteGroupGetTestCase(DeleteTests):

	def __init__(self, *args, **kwargs):
		self.constants_object = V3Constants_Results()
		super(V3_ResultsServer405DeleteGroupGetTestCase, self).__init__(ServerTestV3_results, self.constants_object, *args, **kwargs)

	def test_Server405DeleteGroupGetTestCase(self):
		self.notAllowedDeleteTest(url=self.constants_object.URL_USER_POST, bodyDataExtracter=URL_Delete_Group())
	
if __name__ == '__main__':
	import unittest
	unittest.main()
