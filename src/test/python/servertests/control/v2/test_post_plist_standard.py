from url_functionality import URL_Create
from servertests.control import URLFunctionality
from servertests.control.v2 import V2TestCase

class PlistStandardPostTest(V2TestCase):
	
	def test_Server201PlistFormatPostTestCase(self):
		tester = self.controller()
		bodyDataExtracter = URL_Create()
		expectedValues = URLFunctionality()
		
		oldGroup = tester.getBody(self.URL_post)
		oldGroupTime = tester.getLastModified(self.URL_post)
		tester.postTest(self.URL_post, self.postPut_info, bodyDataExtracter=bodyDataExtracter, fmt=self.plist)
		modifiedTimeID = tester.getLastModified(self.URL_post, ID=bodyDataExtracter.id)
		modifiedTimeGrp = tester.getLastModified(self.URL_post)
		expectedValues.setValues(code=self.SuccessfulAdd, body=self.postPut_return, lastModified=modifiedTimeID)
		
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to post to")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'modifiedTimeGrp unexpectedly not greater than modifiedTimeID')
		self.assertLess(oldGroupTime, modifiedTimeGrp, 'oldGroupTime unexpectedly greater than modifiedTimeGrp')
		self.assertRaises(KeyError, self.test.postException, oldGroup, bodyDataExtracter.id)
		
if __name__ == '__main__':
	import unittest
	unittest.main()
