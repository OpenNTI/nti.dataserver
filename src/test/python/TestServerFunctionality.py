import urllib2
import sys
import os
import subprocess
import time
import unittest

class ServerFunction(object):

	def __init__(self):
		self.server = None

	def starterUp(this, path):
		this.server = subprocess.Popen(sys.executable + " " + path, shell=True)

	def terminateServer(self):
		self.server.terminate()

	def post(self, URL, string, username, password):
		f = urllib2.Request(url = URL, data = string)
		auth = urllib2.HTTPPasswordMgrWithDefaultRealm()
		auth.add_password(None, URL, username, password)
		authendicated = urllib2.HTTPBasicAuthHandler(auth)
		opener = urllib2.build_opener(authendicated)
		urllib2.install_opener(opener)
		try:
			e = urllib2.urlopen(f)
			item = urllib2.urlopen(URL)
			return (e.code, item.read())
		except urllib2.HTTPError, e:
			return (e.code, None)

	def get(self, URL, username, password):
		f = urllib2.Request(url = URL)
		auth = urllib2.HTTPPasswordMgrWithDefaultRealm()
		auth.add_password(None, URL, username, password)
		authendicated = urllib2.HTTPBasicAuthHandler(auth)
		opener = urllib2.build_opener(authendicated)
		urllib2.install_opener(opener)
		try:
			e = urllib2.urlopen(f)
			item = urllib2.urlopen(URL)
			return (e.code, item.read())
		except urllib2.HTTPError, e:
			return (e.code, None)

class ServerTestCase(unittest.TestCase):

	def __init__(self,*args):
		unittest.TestCase.__init__(self,*args)
		self.longMessage = True

	@classmethod
	def setUpClass(cls):

		ServerTestCase.URL_key		  = "http://localhost:8080/dataserver/Test_key"
		ServerTestCase.URL_group_key  = "http://localhost:8080/dataserver/Group/Test_key"
		ServerTestCase.URL_group_1st  = "http://localhost:8080/dataserver/MultiKey/keyOne"
		ServerTestCase.URL_group_2nd  = "http://localhost:8080/dataserver/MultiKey/keyTwo"
		ServerTestCase.URL_group_3rd  = "http://localhost:8080/dataserver/MultiKey/keyThree"
		ServerTestCase.username = 'TestPerson'
		ServerTestCase.password = 'temp001'
		ServerTestCase.default_info = 'starting info'


		ServerTestCase.controler = ServerFunction()
		server_path = os.path.dirname(__file__) + \
			"/../python/app.py"
		ServerTestCase.controler.starterUp(server_path)
		time.sleep(1)

	@classmethod
	def tearDownClass(cls):
		ServerTestCase.controler.terminateServer()

	def setUp(self):

		ServerTestCase.controler.post(ServerTestCase.URL_key, ServerTestCase.default_info,
									  ServerTestCase.username, ServerTestCase.password)
		ServerTestCase.controler.post(ServerTestCase.URL_group_key, ServerTestCase.default_info,
									  ServerTestCase.username, ServerTestCase.password)
		ServerTestCase.controler.post(ServerTestCase.URL_group_1st, ServerTestCase.default_info,
									  ServerTestCase.username, ServerTestCase.password)
		ServerTestCase.controler.post(ServerTestCase.URL_group_2nd, ServerTestCase.default_info,
									  ServerTestCase.username, ServerTestCase.password)
		ServerTestCase.controler.post(ServerTestCase.URL_group_3rd, ServerTestCase.default_info,
									  ServerTestCase.username, ServerTestCase.password)

	def test_Server200GetTestCaseKey(self):

		self.users_URL		  = ServerTestCase.URL_key
		self.username		  = ServerTestCase.username
		self.password		  = ServerTestCase.password
		self.expected_value	  = (200, ServerTestCase.default_info)

		self.actual_value	  = ServerTestCase.controler.get(self.users_URL, self.username, \
									self.password)
		message				  = 'expecting a return value of \"%s,\" received \"%s\"' \
									% (self.expected_value, self.actual_value)
		self.assertEqual(self.expected_value, self.actual_value, message)

	def test_Server401NoUsernameGetTestCaseKey(self):

		self.users_URL		  = ServerTestCase.URL_key
		self.username		  = ''
		self.password		  = ServerTestCase.password
		self.expected_value	  = (401, None)

		self.actual_value	  = ServerTestCase.controler.get(self.users_URL, self.username, \
									self.password)
		message				  = 'expecting a return value of \"%s,\" received \"%s\"' \
									% (self.expected_value, self.actual_value)
		self.assertEqual(self.expected_value, self.actual_value, message)

	def test_Server401NoPasswordGetTestCaseKey(self):

		self.users_URL		  = ServerTestCase.URL_key
		self.username		  = ServerTestCase.username
		self.password		  = 'incorrect'
		self.expected_value	  = (401, None)

		self.actual_value	  = ServerTestCase.controler.get(self.users_URL, self.username, \
									self.password)
		message				  = 'expecting a return value of \"%s,\" received \"%s\"' \
									% (self.expected_value, self.actual_value)
		self.assertEqual(self.expected_value, self.actual_value, message)

	def test_Server404GetTestCaseKey(self):

		self.users_URL		  = "http://localhost:8080/dataserver/doesNotExsist"
		self.username		  = ServerTestCase.username
		self.password		  = ServerTestCase.password
		self.expected_value	  = (404, None)

		self.actual_value	  = ServerTestCase.controler.get(self.users_URL, self.username, \
									self.password)
		message				  = 'expecting a return value of \"%s,\" received \"%s\"' \
									% (self.expected_value, self.actual_value)
		self.assertEqual(self.expected_value, self.actual_value, message)

	def test_Server200PostTestCaseKey(self):

		self.users_URL		  = ServerTestCase.URL_key
		self.username		  = ServerTestCase.username
		self.password		  = ServerTestCase.password
		self.info			  = 'information posted'
		self.expected_value	  = (200, self.info)

		self.actual_value	  = ServerTestCase.controler.post(self.users_URL, self.info, self.username, \
									self.password)
		message				  = 'expecting a return value of \"%s,\" received \"%s\"' \
									% (self.expected_value, self.actual_value)
		self.assertEqual(self.expected_value, self.actual_value, message)


	def test_Server401NoUsernamePostTestCaseKey(self):

		self.users_URL		  = ServerTestCase.URL_key
		self.username		  = ''
		self.password		  = ServerTestCase.password
		self.info			  = 'information posted'
		self.expected_value	  = (401, None)

		self.actual_value	  = ServerTestCase.controler.post(self.users_URL, self.info, self.username, \
									self.password)
		message				  = 'expecting a return value of \"%s,\" received \"%s\"' \
									% (self.expected_value, self.actual_value)
		self.assertEqual(self.expected_value, self.actual_value, message)

	def test_Server401NoPasswordPostTestCaseKey(self):

		self.users_URL		  = ServerTestCase.URL_key
		self.username		  = ServerTestCase.username
		self.password		  = 'incorrect'
		self.info			  = 'information posted'
		self.expected_value	  = (401, None)

		self.actual_value	  = ServerTestCase.controler.post(self.users_URL, self.info, self.username, \
									self.password)
		message				  = 'expecting a return value of \"%s,\" received \"%s\"' \
									% (self.expected_value, self.actual_value)
		self.assertEqual(self.expected_value, self.actual_value, message)

	def test_Server200GetTestCaseGroupKey(self):

		self.users_URL		  = ServerTestCase.URL_group_key
		self.username		  = ServerTestCase.username
		self.password		  = ServerTestCase.password
		self.expected_value	  = (200, ServerTestCase.default_info)

		self.actual_value	  = ServerTestCase.controler.get(self.users_URL, self.username, \
									self.password)
		message				  = 'expecting a return value of \"%s,\" received \"%s\"' \
									% (self.expected_value, self.actual_value)
		self.assertEqual(self.expected_value, self.actual_value, message)

	def test_Server401NoUsernameGetTestCaseGroupKey(self):

		self.users_URL		  = ServerTestCase.URL_group_key
		self.username		  = ''
		self.password		  = ServerTestCase.password
		self.expected_value	  = (401, None)

		self.actual_value	  = ServerTestCase.controler.get(self.users_URL, self.username, \
									self.password)
		message				  = 'expecting a return value of \"%s,\" received \"%s\"' \
									% (self.expected_value, self.actual_value)
		self.assertEqual(self.expected_value, self.actual_value, message)

	def test_Server401NoPasswordGetTestCaseGroupKey(self):

		self.users_URL		  = ServerTestCase.URL_group_key
		self.username		  = ServerTestCase.username
		self.password		  = 'incorrect'
		self.expected_value	  = (401, None)

		self.actual_value	  = ServerTestCase.controler.get(self.users_URL, self.username, \
									self.password)
		message				  = 'expecting a return value of \"%s,\" received \"%s\"' \
									% (self.expected_value, self.actual_value)
		self.assertEqual(self.expected_value, self.actual_value, message)

	def test_Server404NonExsistGroupGetTestCaseGroupKey(self):

		self.users_URL		  = "http://localhost:8080/dataserver/doesNotExsist/Test_key"
		self.username		  = ServerTestCase.username
		self.password		  = ServerTestCase.password
		self.expected_value	  = (404, None)

		self.actual_value	  = ServerTestCase.controler.get(self.users_URL, self.username, \
									self.password)
		message				  = 'expecting a return value of \"%s,\" received \"%s\"' \
									% (self.expected_value, self.actual_value)
		self.assertEqual(self.expected_value, self.actual_value, message)

	def test_Server404NonExsistKeyGetTestCaseGroupKey(self):

		self.users_URL		  = "http://localhost:8080/dataserver/Group/doesNotExsist"
		self.username		  = ServerTestCase.username
		self.password		  = ServerTestCase.password
		self.expected_value	  = (404, None)

		self.actual_value	  = ServerTestCase.controler.get(self.users_URL, self.username, \
									self.password)
		message				  = 'expecting a return value of \"%s,\" received \"%s\"' \
									% (self.expected_value, self.actual_value)
		self.assertEqual(self.expected_value, self.actual_value, message)

	def test_Server200PostTestCaseGroupKey(self):

		self.users_URL		  = ServerTestCase.URL_group_key
		self.username		  = ServerTestCase.username
		self.password		  = ServerTestCase.password
		self.info			  = 'information posted'
		self.expected_value	  = (200, self.info)

		self.actual_value	  = ServerTestCase.controler.post(self.users_URL, self.info, self.username, \
									self.password)
		message				  = 'expecting a return value of \"%s,\" received \"%s\"' \
									% (self.expected_value, self.actual_value)
		self.assertEqual(self.expected_value, self.actual_value, message)

	def test_Server401NoUsernamePostTestCaseGroupKey(self):

		self.users_URL		  = ServerTestCase.URL_group_key
		self.username		  = ''
		self.password		  = ServerTestCase.password
		self.info			  = 'information posted'
		self.expected_value	  = (401, None)

		self.actual_value	  = ServerTestCase.controler.post(self.users_URL, self.info, self.username, \
									self.password)
		message				  = 'expecting a return value of \"%s,\" received \"%s\"' \
									% (self.expected_value, self.actual_value)
		self.assertEqual(self.expected_value, self.actual_value, message)

	def test_Server401NoPasswordPostTestCaseGroupKey(self):

		self.users_URL		  = ServerTestCase.URL_group_key
		self.username		  = ServerTestCase.username
		self.password		  = 'incorrect'
		self.info			  = 'information posted'
		self.expected_value	  = (401, None)

		self.actual_value	  = ServerTestCase.controler.post(self.users_URL, self.info, self.username, \
									self.password)
		message				  = 'expecting a return value of \"%s,\" received \"%s\"' \
									% (self.expected_value, self.actual_value)
		self.assertEqual(self.expected_value, self.actual_value, message)

	def test_Server200GetTestCaseGroup(self):

		self.users_URL_1st		  = ServerTestCase.URL_group_1st
		self.users_URL_2nd		  = ServerTestCase.URL_group_2nd
		self.users_URL_3rd		  = ServerTestCase.URL_group_3rd
		self.username		  = ServerTestCase.username
		self.password		  = ServerTestCase.password
		self.expected_value	  = ((200, ServerTestCase.default_info), (200, ServerTestCase.default_info),
								 (200, ServerTestCase.default_info))
		self.valueOne		  = ServerTestCase.controler.get(self.users_URL_1st, self.username, self.password)
		self.valueTwo		  = ServerTestCase.controler.get(self.users_URL_2nd, self.username, self.password)
		self.valueThree		  = ServerTestCase.controler.get(self.users_URL_3rd, self.username, self.password)
		self.actual_value	  = (self.valueOne, self.valueTwo, self.valueThree)
		message				  = 'expecting return values of %s, %s, and %s,\n' \
									 '					  received %s, %s, and %s instead' \
									% (self.expected_value[0], self.expected_value[1], self.expected_value[2],
									   self.actual_value[0], self.actual_value[1], self.actual_value[2])
		self.assertEqual(self.expected_value, self.actual_value, message)

	def test_Server401NoUsernameGetTestCaseGroup(self):

		self.users_URL_1st		  = ServerTestCase.URL_group_1st
		self.users_URL_2nd		  = ServerTestCase.URL_group_2nd
		self.users_URL_3rd		  = ServerTestCase.URL_group_3rd
		self.username		  = ''
		self.password		  = ServerTestCase.password
		self.expected_value	  = ((401, None), (401, None), (401, None))
		self.valueOne		  = ServerTestCase.controler.get(self.users_URL_1st, self.username, self.password)
		self.valueTwo		  = ServerTestCase.controler.get(self.users_URL_2nd, self.username, self.password)
		self.valueThree		  = ServerTestCase.controler.get(self.users_URL_3rd, self.username, self.password)
		self.actual_value	  = (self.valueOne, self.valueTwo, self.valueThree)
		message				  = 'expecting return values of %s, %s, and %s,\n' \
									 '					  received %s, %s, and %s instead' \
									% (self.expected_value[0], self.expected_value[1], self.expected_value[2],
									   self.actual_value[0], self.actual_value[1], self.actual_value[2])
		self.assertEqual(self.expected_value, self.actual_value, message)

	def test_Server401NoPasswordGetTestCaseGroup(self):

		self.users_URL_1st		  = ServerTestCase.URL_group_1st
		self.users_URL_2nd		  = ServerTestCase.URL_group_2nd
		self.users_URL_3rd		  = ServerTestCase.URL_group_3rd
		self.username		  = ServerTestCase.username
		self.password		  = 'incorrect'
		self.expected_value	  = ((401, None), (401, None), (401, None))
		self.valueOne		  = ServerTestCase.controler.get(self.users_URL_1st, self.username, self.password)
		self.valueTwo		  = ServerTestCase.controler.get(self.users_URL_2nd, self.username, self.password)
		self.valueThree		  = ServerTestCase.controler.get(self.users_URL_3rd, self.username, self.password)
		self.actual_value	  = (self.valueOne, self.valueTwo, self.valueThree)
		message				  = 'expecting return values of %s, %s, and %s,\n' \
									 '					  received %s, %s, and %s instead' \
									% (self.expected_value[0], self.expected_value[1], self.expected_value[2],
									   self.actual_value[0], self.actual_value[1], self.actual_value[2])
		self.assertEqual(self.expected_value, self.actual_value, message)

	def test_Server404NonExsistKeyGetTestCaseGroup(self):

		self.users_URL_1st		  = "http://localhost:8080/dataserver/MultiKey/doesNotExsist"
		self.users_URL_2nd		  = ServerTestCase.URL_group_2nd
		self.users_URL_3rd		  = ServerTestCase.URL_group_3rd
		self.username		  = ServerTestCase.username
		self.password		  = ServerTestCase.password
		self.expected_value	  = ((404, None), (200, ServerTestCase.default_info), (200, ServerTestCase.default_info))
		self.valueOne		  = ServerTestCase.controler.get(self.users_URL_1st, self.username, self.password)
		self.valueTwo		  = ServerTestCase.controler.get(self.users_URL_2nd, self.username, self.password)
		self.valueThree		  = ServerTestCase.controler.get(self.users_URL_3rd, self.username, self.password)
		self.actual_value	  = (self.valueOne, self.valueTwo, self.valueThree)
		message				  = 'expecting return values of %s, %s, and %s,\n' \
									 '					  received %s, %s, and %s instead' \
									% (self.expected_value[0], self.expected_value[1], self.expected_value[2],
									   self.actual_value[0], self.actual_value[1], self.actual_value[2])
		self.assertEqual(self.expected_value, self.actual_value, message)

	def test_Server404NonExsistGroupGetTestCaseGroup(self):

		self.users_URL_1st		  = "http://localhost:8080/dataserver/doesNotExsist/keyOne"
		self.users_URL_2nd		  = ServerTestCase.URL_group_2nd
		self.users_URL_3rd		  = ServerTestCase.URL_group_3rd
		self.username		  = ServerTestCase.username
		self.password		  = ServerTestCase.password
		self.expected_value	  = ((404, None), (200, ServerTestCase.default_info), (200, ServerTestCase.default_info))
		self.valueOne		  = ServerTestCase.controler.get(self.users_URL_1st, self.username, self.password)
		self.valueTwo		  = ServerTestCase.controler.get(self.users_URL_2nd, self.username, self.password)
		self.valueThree		  = ServerTestCase.controler.get(self.users_URL_3rd, self.username, self.password)
		self.actual_value	  = (self.valueOne, self.valueTwo, self.valueThree)
		message				  = 'expecting return values of %s, %s, and %s,\n' \
									 '					  received %s, %s, and %s instead' \
									% (self.expected_value[0], self.expected_value[1], self.expected_value[2],
									   self.actual_value[0], self.actual_value[1], self.actual_value[2])
		self.assertEqual(self.expected_value, self.actual_value, message)

	def test_Server200PostTestCaseGroup(self):

		self.users_URL_1st		  = ServerTestCase.URL_group_1st
		self.users_URL_2nd		  = ServerTestCase.URL_group_2nd
		self.users_URL_3rd		  = ServerTestCase.URL_group_3rd
		self.username		  = ServerTestCase.username
		self.password		  = ServerTestCase.password
		self.info			  = 'information posted'
		self.expected_value	  = ((200, self.info), (200, self.info), (200, self.info))
		self.valueOne		  = ServerTestCase.controler.post(self.users_URL_1st, self.info,
															  self.username, self.password)
		self.valueTwo		  = ServerTestCase.controler.post(self.users_URL_2nd, self.info,
															  self.username, self.password)
		self.valueThree		  = ServerTestCase.controler.post(self.users_URL_3rd, self.info,
															  self.username, self.password)
		self.actual_value	  = (self.valueOne, self.valueTwo, self.valueThree)
		message				  = 'expecting return values of %s, %s, and %s,\n' \
									 '					  received %s, %s, and %s instead' \
									% (self.expected_value[0], self.expected_value[1], self.expected_value[2],
									   self.actual_value[0], self.actual_value[1], self.actual_value[2])
		self.assertEqual(self.expected_value, self.actual_value, message)

	def test_Server401NoUsernamePostTestCaseGroup(self):

		self.users_URL_1st		  = ServerTestCase.URL_group_1st
		self.users_URL_2nd		  = ServerTestCase.URL_group_2nd
		self.users_URL_3rd		  = ServerTestCase.URL_group_3rd
		self.username		  = ''
		self.password		  = ServerTestCase.password
		self.info			  = 'information posted'
		self.expected_value	  = ((401, None), (401, None), (401, None))
		self.valueOne		  = ServerTestCase.controler.post(self.users_URL_1st, self.info,
															  self.username, self.password)
		self.valueTwo		  = ServerTestCase.controler.post(self.users_URL_2nd, self.info,
															  self.username, self.password)
		self.valueThree		  = ServerTestCase.controler.post(self.users_URL_3rd, self.info,
															  self.username, self.password)
		self.actual_value	  = (self.valueOne, self.valueTwo, self.valueThree)
		message				  = 'expecting return values of %s, %s, and %s,\n' \
									 '					  received %s, %s, and %s instead' \
									% (self.expected_value[0], self.expected_value[1], self.expected_value[2],
									   self.actual_value[0], self.actual_value[1], self.actual_value[2])
		self.assertEqual(self.expected_value, self.actual_value, message)

	def test_Server401NoPasswordPostTestCaseGroup(self):

		self.users_URL_1st		  = ServerTestCase.URL_group_1st
		self.users_URL_2nd		  = ServerTestCase.URL_group_2nd
		self.users_URL_3rd		  = ServerTestCase.URL_group_3rd
		self.username		  = ServerTestCase.username
		self.password		  = 'incorrect'
		self.info			  = 'information posted'
		self.expected_value	  = ((401, None), (401, None), (401, None))
		self.valueOne		  = ServerTestCase.controler.post(self.users_URL_1st, self.info,
															  self.username, self.password)
		self.valueTwo		  = ServerTestCase.controler.post(self.users_URL_2nd, self.info,
															  self.username, self.password)
		self.valueThree		  = ServerTestCase.controler.post(self.users_URL_3rd, self.info,
															  self.username, self.password)
		self.actual_value	  = (self.valueOne, self.valueTwo, self.valueThree)
		message				  = 'expecting return values of %s, %s, and %s,\n' \
									 '					  received %s, %s, and %s instead' \
									% (self.expected_value[0], self.expected_value[1], self.expected_value[2],
									   self.actual_value[0], self.actual_value[1], self.actual_value[2])
		self.assertEqual(self.expected_value, self.actual_value, message)

if __name__ == '__main__':
	unittest.main()

