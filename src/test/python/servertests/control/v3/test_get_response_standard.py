from url_functionality import URL_Default
from url_functionality import URL_IDExtracter
from servertests.control import URLFunctionality
from servertests.control import NoFormat
from servertests.control.v3 import V3TestCase

class GetResponseStandardTest(V3TestCase):

	def test_Server200DefaultGetResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = self.controller_response()
		expectedValues    = URLFunctionality()
#		self.defaultSetterQuizResponse(tester)
		tester.getTest(tester.addID(self.URL_resp_NoFormat, self.NoFormat_resp_ID), bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = tester.getLastModified(tester.addID(self.URL_resp_NoFormat, self.NoFormat_resp_ID))
		expectedValues.setValues(code=self.OK, body=self.correct_return, lastModified=modifiedTime, 
								ifModifiedSinceError=self.NotModifiedSince, ifModifiedSinceSuccess=self.OK)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Expected to be Equal')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceError, expectedValues.ifModifiedSinceError, 'If-Modified_Since result supposed to be 304')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceSuccess, expectedValues.ifModifiedSinceSuccess, 'If-Modified_Since result supposed to be 200')
		#print '26'
		
	def test_Server200DefaultGetResponseGroupTestCase(self):
		bodyDataExtracter = URL_IDExtracter()
		tester			  = self.controller_response()
		expectedValues    = URLFunctionality()
#		self.defaultSetterQuizResponse(tester)
		tester.getTest(self.URL_resp_NoFormat, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = tester.getLastModified(self.URL_resp_NoFormat)
		expectedValues.setValues(code=self.OK, body=self.correct_return, lastModified=modifiedTime, 
								ifModifiedSinceError=self.NotModifiedSince, ifModifiedSinceSuccess=self.OK)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,(bodyDataExtracter.body, expectedValues.body, 'Body is supposed to exist as this'))
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Expected to be Equal')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceError, expectedValues.ifModifiedSinceError, 'If-Modified_Since result supposed to be 304')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceSuccess, expectedValues.ifModifiedSinceSuccess, 'If-Modified_Since result supposed to be 200')

if __name__ == '__main__':
	import unittest
	unittest.main()
