'''
Created on Oct 25, 2011

@author: ltesti
'''

from servertests.generalpurpose import V3Constants_Results
from servertests.generalpurpose.puttestcase import PutTests
from servertests.generalpurpose.utilities.catagory import ServerTestV3_results

class V3ResultsServerIncrementingIDsTestCase(PutTests):

	def __init__(self, *args, **kwargs):
		self.constants_object = V3Constants_Results()
		super(V3ResultsServerIncrementingIDsTestCase, self).__init__(ServerTestV3_results, self.constants_object, *args, **kwargs)

	def test_IncrementingIDsTestCase(self):
		self.assertEqual(int(self.incrementingIDs[0]) + 1, int(self.incrementingIDs[1]), 'The ids when posting to the server are not incrementing properly')
	
if __name__ == '__main__':
	import unittest
	unittest.main()