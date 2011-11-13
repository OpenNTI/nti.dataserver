'''
Created on Oct 4, 2011

@author: ltesti
'''

import json
import plistlib
import cStringIO

class FormatFunctionality(object):

	def urlFormat(self, URL, fmt):
		return URL + '?format=' + fmt

	def read(self): pass

	def write(self): pass

class NoFormat(FormatFunctionality):

	def formatURL(self, URL):
		return URL

	def write(self, data):
		return json.dumps(data)

	def read(self, request):
		return json.loads(request.read())

class JsonFormat(NoFormat):

	def formatURL(self, URL):
		return self.urlFormat(URL, 'json')

class PlistFormat(FormatFunctionality):

	def formatURL(self, URL):
		return self.urlFormat(URL, 'plist')

	def write(self, data):
		output = cStringIO.StringIO()
		plistlib.writePlist(data, output)
		data = output.getvalue()
		output.close()
		return data

	def read(self, request):
		return plistlib.readPlistFromString(request.read())