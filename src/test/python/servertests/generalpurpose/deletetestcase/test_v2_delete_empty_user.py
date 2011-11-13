'''
Created on Oct 18, 2011

@author: ltesti
'''

from servertests.generalpurpose import V2Constants
from servertests.generalpurpose.deletetestcase import DeleteTests
from servertests.generalpurpose.utilities.catagory import ServerTestV2

class V2Server401EmptyUserGetTestCase(DeleteTests):

	def __init__(self, *args, **kwargs):
		self.constants_object = V2Constants()
		super(V2Server401EmptyUserGetTestCase, self).__init__(ServerTestV2, self.constants_object, *args, **kwargs)

	def test_Server401EmptyUserGetTestCase(self):
		self.unauthorizedDeleteTest(username=self.constants_object.otherUser, overRide=True)
	
if __name__ == '__main__':
	import unittest
	unittest.main()
