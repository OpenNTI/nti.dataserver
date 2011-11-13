'''
Created on Oct 10, 2011

@author: ltesti
'''

from servertests.generalpurpose import V3Constants_Results
from servertests.generalpurpose.posttestcase import PostTests
from servertests.generalpurpose.utilities.catagory import ServerTestV3_results
from servertests.generalpurpose.utilities.url_formatter import PlistFormat

class V3_ResultsServer201PlistFormatIncorrectAnswerPostTestCase(PostTests):

	def __init__(self, *args, **kwargs):
		self.constants_object = V3Constants_Results()
		super(V3_ResultsServer201PlistFormatIncorrectAnswerPostTestCase, self).__init__(ServerTestV3_results, self.constants_object, *args, **kwargs)

	def test_Server201PlistFormatIncorrectAnswerPostTestCase(self):
		self.successfulAddPostTest(data=self.constants_object.INCORRECT_INFO, body=self.constants_object.INCORRECT_RETURN, fmt=PlistFormat())
	
if __name__ == '__main__':
	import unittest
	unittest.main()