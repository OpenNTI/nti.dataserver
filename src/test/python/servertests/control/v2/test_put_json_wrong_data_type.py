from url_functionality import URL_Default
from servertests.control import URLFunctionality
from servertests.control.v2 import V2TestCase

class JsonStandardPutTest(V2TestCase):

	def test_Server500PlistFormatWrongDatatypePutTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = self.controller()
		expectedValues    = URLFunctionality()
		
		modifiedTime	 = tester.getLastModified(self.URL_plist)
		oldGroupTime	 = tester.getLastModified(self.URL_post)
		tester.putTest(self.URL_plist, self.WrongType, bodyDataExtracter=bodyDataExtracter)
		modifiedTimeID   = tester.getLastModified(self.URL_plist)
		modifiedTimeGrp  = tester.getLastModified(self.URL_post)
		expectedValues.setValues(code=self.WrongType, body=self.default_return, lastModified=modifiedTime)
		
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do bad info")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Incorrect Body')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Wrong ID modification time')
		self.assertGreaterEqual(modifiedTimeGrp, modifiedTimeID, 'Wrong group modification time')
		self.assertEqual(oldGroupTime, modifiedTimeGrp, 'Wrong group modification time')

if __name__ == '__main__':
	import unittest
	unittest.main()
