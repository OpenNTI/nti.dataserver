from url_functionality import URL_Default
from servertests.control import URLFunctionality
from servertests.control.v2 import V2TestCase

class OtherPersonGetTest(V2TestCase):
	
	def test_Server200OtherPersonsPathGetTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = self.controller()
		expectedValues    = URLFunctionality()
		
		tester.getTest(self.URL_json, username=self.otherUser, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = tester.getLastModified(self.URL_json)
		expectedValues.setValues(code=self.OK, body=self.default_return, lastModified=modifiedTime, 
								ifModifiedSinceError=self.NotModifiedSince, ifModifiedSinceSuccess=self.OK)
		
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL and read URL to read from")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceError, expectedValues.ifModifiedSinceError, 'If-Modified_Since result supposed to be 304')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceSuccess, expectedValues.ifModifiedSinceSuccess, 'If-Modified_Since result supposed to be 200')

if __name__ == '__main__':
	import unittest
	unittest.main()