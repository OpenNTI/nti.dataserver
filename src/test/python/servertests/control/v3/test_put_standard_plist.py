from url_functionality import URL_Default
from url_functionality import URLFunctionality
from servertests.control.v3 import V3TestCase

class PlistStandardTest(V3TestCase):

	def test_Server200PlistFormatPutTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = self.controller_quiz()
		expectedValues    = URLFunctionality()
		self.defaultSetterQuiz(tester)
		oldGroup		 = tester.getBody(self.URL_post, fmt=self.plist)
		modifiedTimeOld	 = tester.getLastModified(self.URL_post)
		tester.putTest(self.URL_plist, data=self.put_questions, bodyDataExtracter=bodyDataExtracter, fmt=self.plist)
		modifiedTimeID   = tester.getLastModified(self.URL_NoFormat)
		modifiedTime  = tester.getLastModified(self.URL_post)
		expectedValues.setValues(code=self.OK, body=self.put_answer)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Body is supposed to exist as this')
		self.assertEqual(bodyDataExtracter.lastModified, modifiedTimeID, 'Expected to be Equal')
		self.assertLess(modifiedTimeOld, modifiedTime, 'modifiedTimeOld unexpectedly greater than modifiedTime')
		self.assertNotEqual(oldGroup, bodyDataExtracter.body, 'not supposed to be equal')

if __name__ == '__main__':
	import unittest
	unittest.main()
