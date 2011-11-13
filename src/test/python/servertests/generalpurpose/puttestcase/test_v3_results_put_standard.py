'''
Created on Oct 10, 2011

@author: ltesti
'''

from servertests.generalpurpose import V3Constants_Results
from servertests.generalpurpose.puttestcase import PutTests
from servertests.generalpurpose.utilities.catagory import ServerTestV3_results

class V3_ResultsServer405StandardPutTestCase(PutTests):

	def __init__(self, *args, **kwargs):
		self.constants_object = V3Constants_Results()
		super(V3_ResultsServer405StandardPutTestCase, self).__init__(ServerTestV3_results, self.constants_object, *args, **kwargs)

	def test_Server405StandardPutTestCase(self):
		self.notAllowedPutTest()
	
if __name__ == '__main__':
	import unittest
	unittest.main()