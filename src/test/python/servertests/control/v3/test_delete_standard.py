from url_functionality import URL_Default
from url_functionality import URL_QuizGroup
from servertests.control import URLFunctionality
from servertests.control.v3 import V3TestCase

class DeleteStandardTest(V3TestCase):

	def test_Server204DefaultDeleteTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = self.controller_quiz()
		expectedValues    = URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTimeOld	  = tester.getLastModified(self.URL_post)
		expectedValues.setValues(code=self.SuccessfulDelete, body=self.NotFound)
		tester.deleteTest(self.URL_NoFormat, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = tester.getLastModified(self.URL_post)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Body is supposed to exist as this')
		self.assertGreater(modifiedTime, modifiedTimeOld, 'Wrong modification time')
		self.assertLess(modifiedTimeOld, modifiedTime, 'modifiedTimeOld unexpectedly greater than modifiedTime')
		
	def test_Server405DeleteGroupTestCase(self):
		bodyDataExtracter = URL_QuizGroup()
		tester			  = self.controller_quiz()
		expectedValues    = URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTimeOld	  = tester.getLastModified(self.URL_post)
		expectedValues.setValues(code=self.NotAllowed, body=self.default_answer)
		tester.deleteTest(self.URL_post, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	  = tester.getLastModified(self.URL_post)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Body is supposed to exist as this')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong modification time')
		self.assertEqual(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')

if __name__ == '__main__':
	import unittest
	unittest.main()
