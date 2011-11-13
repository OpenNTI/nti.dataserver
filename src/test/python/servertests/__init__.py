import unittest

from server import DataserverProcess
from server import DataserverClient

class DataServerTestCase(unittest.TestCase):

	#We need to start a dataserver (and stop it)
	#if there is not already one running
	@classmethod
	def setUpClass(cls):
		cls.process = DataserverProcess()
		cls.process.startServer()

	@classmethod
	def tearDownClass(cls):
		cls.process.terminateServer()

	def setUp(self):
		endpoint = getattr(self, 'endpoint', DataserverProcess.ENDPOINT)
		self.ds = DataserverClient(endpoint)
		
	@property
	def client(self):
		return self.ds
	
	@classmethod
	def new_client(cls, credentials=None):
		clt = DataserverClient(DataserverProcess.ENDPOINT)
		if credentials:
			clt.setCredentials(credentials)
		return clt
	