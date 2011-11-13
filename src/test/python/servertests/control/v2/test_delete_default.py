from url_functionality import URL_Default
from servertests.control import URLFunctionality
from servertests.control.v2 import V2TestCase

class DefaultDeleteTest(V2TestCase):

	def test_Server204DefaultDeleteTestCase(self):
		tester = self.controller()
		bodyDataExtracter = URL_Default()
		expectedValues = URLFunctionality()
		
		modifiedTimeOld	 = tester.getLastModified(self.URL_post)
		tester.deleteTest(self.URL_json, bodyDataExtracter=bodyDataExtracter)
		modifiedTime = tester.getLastModified(self.URL_post)
		expectedValues.setValues(code=self.SuccessfulDelete, body=self.NotFound, lastModified=modifiedTime)
		
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to delete to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertGreaterEqual(modifiedTime, modifiedTimeOld, 'Wrong group modification time')

if __name__ == '__main__':
	import unittest
	unittest.main()
