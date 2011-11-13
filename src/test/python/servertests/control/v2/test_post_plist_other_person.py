from url_functionality import URL_oldGroup_json
from servertests.control import URLFunctionality
from servertests.control.v2 import V2TestCase

class PlistOtherPersonPostTest(V2TestCase):
	
	def test_Server403PlistFormatOtherPersonsPathPostTestCase(self):
		tester = self.controller()
		expectedValues = URLFunctionality()
		bodyDataExtracter = URL_oldGroup_json()
				
		modifiedTime = tester.getLastModified(self.URL_post)
		expectedValues.setValues(code=self.Forbidden, body=self.default_return, lastModified=modifiedTime)
		tester.postTest(self.URL_post, self.postPut_info, username=self.otherUser, bodyDataExtracter=bodyDataExtracter)
		
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do to wrong user")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong group modification time')
		
if __name__ == '__main__':
	import unittest
	unittest.main()
