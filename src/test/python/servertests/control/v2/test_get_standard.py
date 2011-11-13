from url_functionality import URL_Group
from url_functionality import URL_Default
from url_functionality import URL_TypeGet
from servertests.control import URLFunctionality
from servertests.control import NoFormat
from servertests.control import VOID_VALUE
from servertests.control.v2 import V2TestCase

class StandardGetTest(V2TestCase):
	
	def _run_test(self, URL, bodyDataExtracter=VOID_VALUE, fmt=NoFormat(), use_equal=True):
		tester = self.controller()
		expectedValues = URLFunctionality()
		
		tester.getTest(URL, bodyDataExtracter=bodyDataExtracter, fmt=fmt)
		modifiedTime = tester.getLastModified(URL)
		expectedValues.setValues(code=self.OK, body=self.default_return, lastModified=modifiedTime,\
								ifModifiedSinceError=self.NotModifiedSince, ifModifiedSinceSuccess=self.OK)
		
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL and read URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Incorrect Body')
		
		if use_equal:
			self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		else:
			self.assertLessEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
			
		self.assertEqual(bodyDataExtracter.ifModifiedSinceError, expectedValues.ifModifiedSinceError, 'If-Modified_Since result supposed to be 304')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceSuccess, expectedValues.ifModifiedSinceSuccess, 'If-Modified_Since result supposed to be 200')
		
	def test_Server200DefaultGetTestCase(self):
		self._run_test(self.URL_json, bodyDataExtracter=URL_Default())

	def test_Server200GroupGetTestCase(self):
		self._run_test(self.URL_post, bodyDataExtracter=URL_Group(), use_equal=False)
		
	def test_Server200TypeGetTestCase(self):
		self._run_test(self.URL_type, bodyDataExtracter=URL_TypeGet())
		
	def test_Server200JsonFormatGetTestCase(self):
		self._run_test(self.URL_json, bodyDataExtracter=URL_Default(), fmt=self.json)

	def test_Server200PlistFormatGetTestCase(self):
		self._run_test(self.URL_plist, bodyDataExtracter=URL_Default(), fmt=self.plist)
		
if __name__ == '__main__':
	import unittest
	unittest.main()
