from url_functionality import URL_Default
from servertests.control import URLFunctionality
from servertests.control.v2 import V2TestCase

class JsonOtherPersonPutTest(V2TestCase):
	
	def test_Server403JsonFormatOtherPersonsPathPutTestCase(self):
		tester = self.controller()
		bodyDataExtracter = URL_Default()
		expectedValues = URLFunctionality()
		
		oldGroupTime = tester.getLastModified(self.URL_post)
		tester.putTest(self.URL_json, data=self.postPut_info, username=self.otherUser, bodyDataExtracter=bodyDataExtracter, fmt=self.json)
		modifiedTimeID = tester.getLastModified(self.URL_json)
		modifiedTimeGrp = tester.getLastModified(self.URL_post)
		expectedValues.setValues(code=self.Forbidden, body=self.default_return, lastModified=modifiedTimeID)
		
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do to wrong user")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertEqual(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		
if __name__ == '__main__':
	import unittest
	unittest.main()
