'''
Created on Oct 18, 2011

@author: ltesti
'''

from servertests.generalpurpose import V3Constants_Results
from servertests.generalpurpose.deletetestcase import DeleteTests
from servertests.generalpurpose.utilities.catagory import ServerTestV3_results

class V3_ResultsServer404NonExistIDGetTestCase(DeleteTests):

	def __init__(self, *args, **kwargs):
		self.constants_object = V3Constants_Results()
		super(V3_ResultsServer404NonExistIDGetTestCase, self).__init__(ServerTestV3_results, self.constants_object, *args, **kwargs)

	def test_Server404NonExistIDGetTestCase(self):
		self.notFoundDeleteTest(url=self.object.URL_NON_EXIST_ID)
	
if __name__ == '__main__':
	import unittest
	unittest.main()
