'''
Created on Oct 10, 2011

@author: ltesti
'''

from servertests.generalpurpose import V3Constants_Results
from servertests.generalpurpose.posttestcase import PostTests
from servertests.generalpurpose.utilities.catagory import ServerTestV3_results

class V3_ResultsServer201StandardPostTestCase(PostTests):

	def __init__(self, *args, **kwargs):
		self.constants_object = V3Constants_Results()
		super(V3_ResultsServer201StandardPostTestCase, self).__init__(ServerTestV3_results, self.constants_object, *args, **kwargs)

	def test_Server201StandardPostTestCase(self):
		self.successfulAddPostTest(body=self.constants_object.DEFAULT_RETURN)
	
if __name__ == '__main__':
	import unittest
	unittest.main()