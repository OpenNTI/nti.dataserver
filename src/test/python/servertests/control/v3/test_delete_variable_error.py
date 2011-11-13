from url_functionality import URL_Default
from servertests.control import URLFunctionality
from servertests.control.v3 import V3TestCase

class DeleteVariableErrorTest(V3TestCase):

	def _run_test(self, expectedValues, URL, password, responseString):
		bodyDataExtracter = URL_Default()
		tester			  = self.controller_quiz()
		self.defaultSetterQuizResponse(tester)
		modifiedTimeOld	  = tester.getLastModified(self.URL_post)
		tester.deleteTest(URL, password=password, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = tester.getLastModified(self.URL_post)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, responseString)
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong modification time')
		self.assertEqual(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')

	def test_Server401IncorrectPasswordDeleteTestCase(self):
		expectedValues    = URLFunctionality()
		expectedValues.setValues(code=self.Unauthorized)
		self._run_test(expectedValues, self.URL_NoFormat, self.incorrectPassword, "Unexpectedly Authorized")

	def test_Server404NonExsistantIDDeleteTestCase(self):
		expectedValues    = URLFunctionality()
		expectedValues.setValues(code=self.NotFound)
		self._run_test(expectedValues, self.URL_NoID, self.password, "Unexpectedly Found")

if __name__ == '__main__':
	import unittest
	unittest.main()
