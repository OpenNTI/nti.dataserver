from url_functionality import URL_Default
from servertests.control import URLFunctionality
from servertests.control import NoFormat
from servertests.control.v3 import V3TestCase

class PostQuizTests(V3TestCase):

	def _run_test(self, fmt=NoFormat()):
		tester = self.controller_quiz()
		bodyDataExtracter = URL_Default()
		expectedValues = URLFunctionality()
		
		modifiedTimeOld = tester.getLastModified(self.URL_post)
		expectedValues.setValues(code=self.NotAllowed)
		tester.postTest(self.URL_post, bodyDataExtracter=bodyDataExtracter, fmt=fmt)
		modifiedTime = tester.getLastModified(self.URL_post)
		
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'URL supposed to be Not allowed')
		self.assertEqual(modifiedTimeOld, modifiedTime, 'Modification time changed')
	
	def test_Server405DefaultPostTestCase(self):
		self._run_test()

	def test_Server405JsonFormatPostTestCase(self):
		self._run_test(fmt=self.json)
		
	def test_Server405PlistFormatPostTestCase(self):
		self._run_test(fmt=self.plist)

if __name__ == '__main__':
	import unittest
	unittest.main()
