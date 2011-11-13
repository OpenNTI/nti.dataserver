from url_functionality import URL_Default
from servertests.control import URLFunctionality
from servertests.control.v3 import V3TestCase

class UnauthorizedGetTests(V3TestCase):

	def test_Server401IncorrectPasswordGetTestCase(self):
		tester= self.controller_quiz()
		bodyDataExtracter = URL_Default()
		expectedValues = URLFunctionality()
		
		tester.getTest(self.URL_NoFormat, password=self.incorrectPassword, bodyDataExtracter=bodyDataExtracter)
		modifiedTime = tester.getLastModified(self.URL_NoFormat)
		
		expectedValues.setValues(code=self.Unauthorized, body=self.TheVoid, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to read')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Expected to be Equal')

if __name__ == '__main__':
	import unittest
	unittest.main()
