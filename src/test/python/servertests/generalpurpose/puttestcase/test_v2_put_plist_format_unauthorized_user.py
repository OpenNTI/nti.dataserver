'''
Created on Oct 10, 2011

@author: ltesti
'''

from servertests.generalpurpose import V2Constants
from servertests.generalpurpose.puttestcase import PutTests
from servertests.generalpurpose.utilities.catagory import ServerTestV2
from servertests.generalpurpose.utilities.body_data_extracter import URL_DefaultV2

class V2Server403PlistFormatUnauthorizedUserPutTestCase(PutTests):

	def __init__(self, *args, **kwargs):
		self.constants_object = V2Constants()
		super(V2Server403PlistFormatUnauthorizedUserPutTestCase, self).__init__(ServerTestV2, self.constants_object, *args, **kwargs)

	def test_Server403PlistFormatUnauthorizedUserPutTestCase(self):
		self.unauthorizedPutTestPlistFormat(username=self.constants_object.otherUser, bodyDataExtracter=URL_DefaultV2(), overRide=True)
	
if __name__ == '__main__':
	import unittest
	unittest.main()