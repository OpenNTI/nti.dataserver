from url_functionality import URL_oldGroup_json
from servertests.control import URLFunctionality
from servertests.control.v2 import V2TestCase

class JsonWrongDataTypePostTest(V2TestCase):
	
	def test_Server500PlistFormatWrongDatatypePostTestCase(self):
		tester = self.controller()
		expectedValues = URLFunctionality()
		bodyDataExtracter = URL_oldGroup_json()
		
		modifiedTime = tester.getLastModified(self.URL_post)
		expectedValues.setValues(code=self.WrongType, body=self.default_return, lastModified=modifiedTime)
		tester.postTest(self.URL_post, data=self.WrongType, bodyDataExtracter=bodyDataExtracter)
		
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do bad info")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong group modification time')
		
if __name__ == '__main__':
	import unittest
	unittest.main()
