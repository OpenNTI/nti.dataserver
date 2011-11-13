'''
Created on Oct 3, 2011

@author: ltesti
'''
from servertests.control.v4.ServerStart import ServerStart
from servertests.control.v4.ServerControl import GetLastModified


class StandardTest(ServerStart):
	
	def __init__(self, clazz, constants, expectedValues, *args, **kwargs):
		super(StandardTest, self).__init__(clazz, constants, expectedValues, *args, **kwargs)
	
	def runTestType(self, class_object, type_object):
		url, info, constants, self.bodyDataExtracter =  class_object.standardTest()
		getModificationTime = GetLastModified()
		lastModifiedTime = getModificationTime.run(url, constants)
		self.expectedValues.lastModified = lastModifiedTime
		type_object.run(constants, url, info, username=constants.username, password=constants.password, bodyDataExtracter=self.bodyDataExtracter)