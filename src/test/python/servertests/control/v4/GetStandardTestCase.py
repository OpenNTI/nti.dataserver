'''
Created on Oct 4, 2011

@author: ltesti
'''

from servertests.control.v4.StandardBehavorTestCase import StandardTest
from servertests.control.v4.ServerControl import GetTest

class V2GetTests(StandardTest):
	
	def standardGetTest(self):
		self.runTestType(self.object, GetTest())
		self.assertResponsePartsEqual(self.bodyDataExtracter)
		self.assertEqual(self.bodyDataExtracter.ifModifiedSinceError, self.expectedValues.ifModifiedSinceError, 'If-Modified_Since result supposed to be 304')
		self.assertEqual(self.bodyDataExtracter.ifModifiedSinceSuccess, self.expectedValues.ifModifiedSinceSuccess, 'If-Modified_Since result supposed to be 200')