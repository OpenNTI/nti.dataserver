from url_functionality import URL_Create
from servertests.control import URLFunctionality
from servertests.control.v2 import V2TestCase

class PlistNonExsistPostTest(V2TestCase):
	
	def _run_test(self, URL):
		tester = self.controller()
		bodyDataExtracter = URL_Create()
		expectedValues = URLFunctionality()
				
		oldGroup = tester.getBody(URL)
		oldGroupTime = tester.getLastModified(URL)
		tester.postTest(URL, self.postPut_info, bodyDataExtracter=bodyDataExtracter, fmt=self.plist)
		modifiedTimeID = tester.getLastModified(URL, ID=bodyDataExtracter.id)
		modifiedTimeGrp = tester.getLastModified(URL)
		expectedValues.setValues(code=self.SuccessfulAdd, body=self.postPut_return, lastModified=modifiedTimeID)
		
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to post to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong group modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID)
		
		return (oldGroup, oldGroupTime, modifiedTimeGrp, bodyDataExtracter.id)
		
	def test_Server201PlistFormatNonExsistantTypePostTestCase(self):
		oldGroup, oldGroupTime, modifiedTimeGrp, bid = self._run_test(self.NoTypeNoID)
		self.assertLess(oldGroupTime, modifiedTimeGrp, 'Group time should have changed')
		self.assertRaises(KeyError, self.test.postException, oldGroup, bid)
		
	def test_Server201PlistFormatNonExsistantGroupPostTestCase(self):
		oldGroup, oldGroupTime, _, bid = self._run_test(self.NoGroupNoID)
		self.assertEqual(oldGroupTime, self.NotFound)
		self.assertRaises(TypeError, self.test.postException, oldGroup, bid)
		
if __name__ == '__main__':
	import unittest
	unittest.main()
