from url_functionality import URL_Create
from servertests.control import URLFunctionality
from servertests.control.v2 import V2TestCase

class JsonNonExsistPostTest(V2TestCase):
	
	def _run_test(self, URL):
		tester = self.controller()
		bodyDataExtracter = URL_Create()
		expectedValues = URLFunctionality()
		
		oldGroup = tester.getBody(URL)
		oldGroupTime = tester.getLastModified(URL)
		tester.postTest(URL, self.postPut_info, bodyDataExtracter=bodyDataExtracter, fmt=self.json)
		modifiedTimeID   = tester.getLastModified(URL, ID=bodyDataExtracter.id)
		modifiedTimeGrp  = tester.getLastModified(URL)
		expectedValues.setValues(code=self.SuccessfulAdd, body=self.postPut_return, lastModified=modifiedTimeID)
		
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to post to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertLess(oldGroupTime, modifiedTimeGrp, 'Group time should have changed')
		self.assertRaises(TypeError, self.test.postException, oldGroup)
		
	def test_Server201JsonFormatNonExsistantTypePostTestCase(self):
		self._run_test(self.NoTypeNoID)

	def test_Server201JsonFormatNonExsistantGroupPostTestCase(self):
		self._run_test(self.NoGroupNoID)
		
if __name__ == '__main__':
	import unittest
	unittest.main()
