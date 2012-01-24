#!/usr/bin/env python

import os, sys
import urllib2
from urlparse import urljoin
from json import JSONEncoder
import plasTeX
from plasTeX.TeX import TeX


def _getSource(nodelist):
	for node in nodelist:
		if node.nodeType == node.ELEMENT_NODE:
			return node.source
	return ''

def _parseLaTeX(file):
	
	document = plasTeX.TeXDocument()
	
	#setup config options we want
	document.config['files']['split-level']=1
	document.config['general']['theme']='mathcounts'

	# Instantiate the TeX processor
	tex = TeX(document, file=file)

	# Populate variables for use later
	document.userdata['jobname'] = tex.jobname
	document.userdata['working-dir'] = os.getcwd()

	# parse
	tex.parse()

	return document
# End _parseLaTeX

def todict(file, idprefix = ''):
	"""
	Return a python dictionary from the specified LaTeX file
	"""
	return _todict(_parseLaTeX(file), idprefix)
	
def _todict(document, idprefix = ''):
	"""
	Return a python dictionary from the specified plasTeX document
	"""
	result = dict()
	result['Items'] = items = dict()
	
	questionId = 1
	for question in document.getElementsByTagName( 'question' ):
		
		answers = list()
		problemSource = None
		
		for problem in question.getElementsByTagName("problem"):			
			problemSource = problem.source
			# break since we should have only one problem per question
			break
			
		for solution in question.getElementsByTagName("solution"):
			t = _getSource(solution.childNodes)
			answers.append(t)
			
		if problemSource and answers:
			qsid = idprefix + str(questionId)
			item = {'ID' : qsid, 'Text' : problemSource, 'Answers' : answers}
			items[qsid] = item
			
		questionId = questionId + 1
	
	return result

def toJSON(file, idprefix = ''):
	"""
	Return a JSON string from the specified LaTeX file
	"""
	return _toJSON(_parseLaTeX(file), idprefix)
	
def _toJSON(document, idprefix = ''):
	"""
	Return a JSON string from the specified plasTeX document
	"""
	return JSONEncoder().encode(_todict(document, idprefix))

def toXml( file, outfile = None ):
	"""
	Save the specified LaTeX file to a plasTeX xml file
	"""
	if not outfile:
		t = os.path.splitext(file)
		outfile = '%s.xml' % t[0]
	
	document = _parseLaTeX(file)
	with open(outfile,'w') as f:
		f.write(document.toXML().encode('utf-8'))
		
	return outfile

def transform(file, format='json', outfile = None):
	
	if format == 'xml':
		return toXml(file, outfile)
	elif format == 'json':
		json = toJSON(file)
		
		if outfile:
			with open(outfile,'w') as f:
				f.write(json)
		
		return json
	else:
		return None
	
def put(file, url, user ='csanchez', password = 'temp001'):
	"""
	Put the json representation of the specified LaTeX file in the specified url
	"""	
	json = toJSON(file)
	return _put(json, url, user, password)

def _put(json, url, user ='csanchez', password = 'temp001'):

	print "\nConnecting to %s ..." % url
	
	urllib2.build_opener(urllib2.HTTPHandler)
	request = urllib2.Request(url, data=json)
	request.add_header('Content-Type', 'application/json')
	request.get_method = lambda: 'PUT'
	
	auth = urllib2.HTTPPasswordMgrWithDefaultRealm()
	auth.add_password(None, url, user, password)
	authendicated = urllib2.HTTPBasicAuthHandler(auth)
	
	opener = urllib2.build_opener(authendicated)
	urllib2.install_opener(opener)
		
	return opener.open(request)
	
def send2server(file, id, server, path, idprefix = ''):
	idpath = urljoin(path, id)
	url = urljoin(server, idpath)
	put(file, url)

if __name__ == '__main__':
	args = sys.argv[1:]
	if args:
		f = lambda a, idx, d: d if len(a) <= idx else a[idx] 
		id 		= f(args, 1, 'mathcounts-2011-0')
		server	= f(args, 2, 'http://curie.local:8080')
		path	= f(args, 3, '/dataserver/quizzes/')
		idprx	= f(args, 4, '') 
		send2server(args[0], id, server, path, idprx)
		
		
		
