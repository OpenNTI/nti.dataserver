from url_functionality import URL_Create
from servertests.control import URLFunctionality
from servertests.control.v2 import V2TestCase

class JsonNonExistPutTest(V2TestCase):
	
	def _run_test(self, URL, putURL, fmt):
		tester = self.controller()
		bodyDataExtracter = URL_Create()
		expectedValues = URLFunctionality()
				
		oldGroup = tester.getBody(URL)
		oldGroupTime = tester.getLastModified(URL)
		tester.putTest(putURL, self.postPut_info, bodyDataExtracter=bodyDataExtracter, fmt=fmt)
		modifiedTimeID = tester.getLastModified(putURL)
		modifiedTimeGrp = tester.getLastModified(URL)
		expectedValues.setValues(code=self.SuccessfulAdd, body=self.postPut_return, lastModified=modifiedTimeID)
		
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to put to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertLess(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')
		self.assertNotEqual(oldGroup, bodyDataExtracter.body, 'body expected to change')
		
	def test_Server201JsonfmtNonExsistantTypePutTestCase(self):
		self._run_test(self.NoTypeGroup, self.NoTypeWithID, self.json)
		
	def test_Server201PlistfmtNonExsistantGroupPutTestCase(self):
		self._run_test(self.NoGroupGroup, self.NoGroupWithID, self.plist)

	def test_Server201PlistfmtNonExsistantIDPutTestCase(self):
		self._run_test(self.URL_post, self.NoID, self.plist)
	
if __name__ == '__main__':
	import unittest
	unittest.main()
