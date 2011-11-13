from url_functionality import URL_Default
from servertests.control import URLFunctionality
from servertests.control import NoFormat
from servertests.control.v3 import V3TestCase

class GetFormattedTests(V3TestCase):

	def _run_test(self, URL, ID, fmt=NoFormat()):
		bodyDataExtracter = URL_Default()
		tester			  = self.controller_response()
		expectedValues    = URLFunctionality()
		tester.getTest(tester.addID(URL, ID), bodyDataExtracter=bodyDataExtracter, fmt=fmt)
		modifiedTime	 = tester.getLastModified(tester.addID(URL, ID))
		expectedValues.setValues(code=self.OK, body=self.correct_return, lastModified=modifiedTime, 
								ifModifiedSinceError=self.NotModifiedSince, ifModifiedSinceSuccess=self.OK)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Expected to be Equal')

	def test_Server200JsonFormatGetResponseTestCase(self):
		self._run_test(self.URL_resp_NoFormat, self.NoFormat_resp_ID, self.json)
		
	def test_Server200PlistFormatGetResponseTestCase(self):
		self._run_test(self.URL_resp_NoFormat, self.NoFormat_resp_ID, fmt=self.plist)
		
	def test_Server200OtherGetResponseTestCase(self):
		self._run_test(self.URL_resp_other, self.Other_resp_ID)

if __name__ == '__main__':
	import unittest
	unittest.main()
