'''
Created on Oct 4, 2011

@author: ltesti
'''

from servertests.generalpurpose import V3Constants_Results
from servertests.generalpurpose.gettestcase import GetTests
from servertests.generalpurpose.utilities.catagory import ServerTestV3_results
from servertests.generalpurpose.utilities.url_formatter import PlistFormat

class V3ResultsServer200PlistFormatGetTestCase(GetTests):

	def __init__(self, *args, **kwargs):
		self.constants_object = V3Constants_Results()
		super(V3ResultsServer200PlistFormatGetTestCase, self).__init__(ServerTestV3_results, self.constants_object, *args, **kwargs)

	def test_Server200PlistFormatGetTestCase(self):
		self.okGetTest(fmt=PlistFormat())
	
if __name__ == '__main__':
	import unittest
	unittest.main()