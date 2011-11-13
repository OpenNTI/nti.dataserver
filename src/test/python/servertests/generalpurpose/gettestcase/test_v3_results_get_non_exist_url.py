'''
Created on Oct 4, 2011

@author: ltesti
'''

from servertests.generalpurpose import V3Constants_Results
from servertests.generalpurpose.gettestcase import GetTests
from servertests.generalpurpose.utilities.catagory import ServerTestV3_results

class V3ResultsServer404NonExistURLGetTestCase(GetTests):

	def __init__(self, *args, **kwargs):
		self.constants_object = V3Constants_Results()
		super(V3ResultsServer404NonExistURLGetTestCase, self).__init__(ServerTestV3_results, self.constants_object, *args, **kwargs)

	def test_Server404NonExistURLGetTestCase(self):
		self.notFoundGetTest(url=self.constants_object.URL_USER_NONEXIST_ID)
	
if __name__ == '__main__':
	import unittest
	unittest.main()