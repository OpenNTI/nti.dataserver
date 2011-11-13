from url_functionality import URL_Default
from url_functionality import URL_QuizGroup
from servertests.control import URLFunctionality
from servertests.control import NoFormat
from servertests.control.v3 import V3TestCase

class StandardGetTests(V3TestCase):

	def _run_test(self, URL, bodyDataExtracter=URL_Default(), fmt=NoFormat()):
		tester = self.controller_quiz()
		expectedValues = URLFunctionality()

		tester.getTest(URL, bodyDataExtracter=bodyDataExtracter, fmt=fmt)
		modifiedTime = tester.getLastModified(URL, fmt=fmt)
		expectedValues.setValues(code=self.OK, body=self.default_answer, lastModified=modifiedTime, 
						ifModifiedSinceError=self.NotModifiedSince, ifModifiedSinceSuccess=self.OK)
		
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to read")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Body is supposed to exist as this')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Expected to be Equal')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceError, expectedValues.ifModifiedSinceError, 'If-Modified_Since result supposed to be 304')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceSuccess, expectedValues.ifModifiedSinceSuccess, 'If-Modified_Since result supposed to be 200')

	def test_Server200DefaultGetTestCase(self):
		self._run_test(self.URL_NoFormat)

	def test_Server200DefaultGetGroupTestCase(self):
		self._run_test(self.URL_post, bodyDataExtracter=URL_QuizGroup())

	def test_Server200JsonFormatGetTestCase(self):
		self._run_test(self.URL_json, fmt=self.json)
		
	def test_Server200PlistFormatGetTestCase(self):
		self._run_test(self.URL_plist, fmt=self.plist)

if __name__ == '__main__':
	import unittest
	unittest.main()
