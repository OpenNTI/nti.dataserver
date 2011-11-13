from url_functionality import URL_Default
from servertests.control import URLFunctionality
from servertests.control import NoFormat
from servertests.control.v3 import V3TestCase

class DeleteFormatTests(V3TestCase):

	def _run_test(self, fmt=NoFormat):
		bodyDataExtracter = URL_Default()
		tester			  = self.controller_quiz()
		expectedValues    = URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTimeOld	  = tester.getLastModified(self.URL_post)
		expectedValues.setValues(code=self.SuccessfulDelete, body=self.NotFound)
		tester.deleteTest(self.URL_NoFormat, bodyDataExtracter=bodyDataExtracter, fmt=fmt)
		modifiedTime	 = tester.getLastModified(self.URL_post)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Body is supposed to exist as this')
		self.assertGreater(modifiedTime, modifiedTimeOld, 'Wrong modification time')
		self.assertLess(modifiedTimeOld, modifiedTime, 'modifiedTimeOld unexpectedly greater than modifiedTime')

	def test_Server204JsonFormatDeleteTestCase(self):
		self._run_test(self.json)
		#print '22'

	def test_Server204PlistFormatDeleteTestCase(self):
		self._run_test(self.plist)

if __name__ == '__main__':
	import unittest
	unittest.main()
