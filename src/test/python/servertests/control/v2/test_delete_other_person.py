from url_functionality import URL_Default
from servertests.control import URLFunctionality
from servertests.control.v2 import V2TestCase

class JsonOtherPersonDeleteTest(V2TestCase):

	def test_Server403JsonFormatOtherPersonsPathDeleteTestCase(self):
		tester = self.controller()
		bodyDataExtracter = URL_Default()
		expectedValues = URLFunctionality()
		
		modifiedTimeOld	 = tester.getLastModified(self.URL_post)
		tester.deleteTest(self.URL_json, username=self.otherUser, bodyDataExtracter=bodyDataExtracter)
		modifiedTime = tester.getLastModified(self.URL_post)
		expectedValues.setValues(code=self.Forbidden, body=self.default_return, lastModified=modifiedTime)
		
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do to wrong user")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong group modification time')

if __name__ == '__main__':
	import unittest
	unittest.main()
