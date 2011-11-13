'''
Created on Oct 18, 2011

@author: ltesti
'''

from servertests.generalpurpose import V2Constants
from servertests.generalpurpose.deletetestcase import DeleteTests
from servertests.generalpurpose.utilities.catagory import ServerTestV2
from servertests.generalpurpose.utilities.body_data_extracter import URL_Group

class V2Server405DeleteGroupGetTestCase(DeleteTests):

	def __init__(self, *args, **kwargs):
		self.constants_object = V2Constants()
		super(V2Server405DeleteGroupGetTestCase, self).__init__(ServerTestV2, self.constants_object, *args, **kwargs)

	def test_Server405DeleteGroupGetTestCase(self):
		self.notAllowedDeleteTest(url=self.constants_object.URL_USER_POST, bodyDataExtracter=URL_Group())
	
if __name__ == '__main__':
	import unittest
	unittest.main()
