from url_functionality import URL_Default
from servertests.control import URLFunctionality
from servertests.control import VOID_VALUE
from servertests.control.v3 import V3TestCase

class VariableErrorGetTests(V3TestCase):

	def _run_test(self, URL, code, password=VOID_VALUE):
		tester = self.controller_quiz()
		bodyDataExtracter = URL_Default()
		expectedValues = URLFunctionality()
		
		tester.getTest(URL, password=password, bodyDataExtracter=bodyDataExtracter)
		modifiedTime = tester.getLastModified(URL)
		expectedValues.setValues(code=code, body=self.TheVoid, lastModified=modifiedTime)
		
		return (bodyDataExtracter, expectedValues)
			
	def test_Server401IncorrectPasswordGetTestCase(self):
		bodyDataExtracter, expectedValues = self._run_test(self.URL_NoFormat, self.Unauthorized, self.incorrectPassword)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to read')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Expected to be Equal')
		
	def test_Server404NonExistantQuizGetTestCase(self):
		bodyDataExtracter, expectedValues = self._run_test(self.URL_NoID, self.NotFound)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'URL supposed to be Not Found')

if __name__ == '__main__':
	import unittest
	unittest.main()
