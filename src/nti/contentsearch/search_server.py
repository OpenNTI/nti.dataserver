import os
import sys

try:
	import plasTeX
except ImportError:
	toAdd = "../../../../../AoPS/src/main/plastex"
	if os.path.dirname( __file__ ):
		toAdd = os.path.abspath(os.path.dirname( __file__ )) + '/' + toAdd

	sys.path.append( toAdd )
	import plasTeX
	assert plasTeX
	
import nti.contentsearch as contentsearch 
from nti.dataserver.wsgi import Get

useTypeAhead = True

class SearchTree(object):

	def __init__( self, indexmanager ):
		
		class GetSearch(Get):
			def __init__(self):
				super(GetSearch,self).__init__( keyName='search')
				self.indexmanager = indexmanager


			def __call__(self, environ, start_response ):
				body = self.getObject( environ )
				return self.doRespond( environ, start_response, body )
	
			def getObject( self, environ, value=None, putIfMissing=False ):
				query =  self.getKey( environ ) 
				if useTypeAhead:
					return self.indexmanager.quick_search(query)
				else:
					return self.indexmanager.search(query)
			
		self.get_search = GetSearch()
			
	def addToSelector( self, application, prefix='/prealgebra' ):
		application.add( prefix + '/Search/{search:segment}[/]', GET=self.get_search )
		
		
DEFAULT_INDEX_DIR	= "/Library/WebServer/Documents/prealgebra/indexdir"
DEFAULT_INDEX_NAME	= "prealgebra"

from selector import Selector

def createApplication( ):
	application = Selector(consume_path=False)
	indexmanager = contentsearch.create_index_manager(DEFAULT_INDEX_DIR, DEFAULT_INDEX_NAME)
	searchTree = SearchTree(indexmanager)
	searchTree.addToSelector(application)
	return application

HTTP_PORT = 8080

if __name__ == '__main__':

	import select
	import platform
	import nti.dataserver
	
	import signal
	def huphandler(signum,frame):
		print "Reloading dataserver code"
		reload(nti.dataserver)
		print "Reloading wsgi code"
		reload(nti.dataserver.wsgi)
		print "done reloading"
	signal.signal( signal.SIGHUP, huphandler )

	print "Send SIGHUP to process", os.getpid(), "to reload code"
	
	from wsgiref.simple_server import make_server

	httpd = make_server( '', HTTP_PORT, createApplication() )
	while True:
		try:
			#SIGHUP could cause this to raise 'interrupted system call'
			print "Starting server %s:%s" % (platform.uname()[1], HTTP_PORT)
			httpd.serve_forever()
		except select.error, e:
			print e
			break