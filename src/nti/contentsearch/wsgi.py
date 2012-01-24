import os

from nti.dataserver.wsgi import Get

USE_TYPE_AHEAD = False

class GetSearch(Get):

	def __init__(self, indexmanager):
		super(GetSearch,self).__init__( keyName='search')
		self.indexmanager = indexmanager

	def getObject( self, environ, value=None, putIfMissing=False ):
		query = self.getKey( environ )

		indexname = self.get_indexname(environ)

		d ={'query':query, 'indexname':indexname}
		return self.indexmanager.quick_search(**d) if USE_TYPE_AHEAD \
				else self.indexmanager.suggest_and_search(**d)

	def get_indexname(self, environ):
		"""
		return the book/content index name
		"""
		path = environ['PATH_INFO'] if 'PATH_INFO' in environ else None
		if not path:
			sm = environ['selector.matches'] if 'selector.matches' in environ else None
			if sm and len(sm) > 0: path = sm[0]

		if path:
			records = path.split('/')
			if records[0] == '':
				path = records[1] if len (records) >= 1 else None
			else:
				path = records[0]

		return path

class UserSearch(Get):

	def __init__( self, indexmanager ):
		super( UserSearch, self ).__init__( keyName='term' )
		self.indexmanager = indexmanager

	def getObject( self, environ, **kwargs ):
		term = self.getKey( environ )
		user = self.getPathUser( environ )
		return self.indexmanager.user_data_search( term, username=user )

class SearchTree(object):

	def __init__( self, parentDirectory, indexmanager):
		super(SearchTree,self).__init__()

		self.base_directory = os.path.join( parentDirectory, 'indexdir' )
		self.indexmanager = indexmanager
		self.get_search = GetSearch( self.indexmanager )
		self.user_search = UserSearch( self.indexmanager )

	def addToSelector( self, application, prefix='/prealgebra', dataserverPrefix='/dataserver' ):
		""" Returns the path we consume, if we consume one. Otherwise none. """
		indexname = prefix[1:]
		if self.indexmanager.add_book(self.base_directory, indexname):
			application.add( prefix + '/Search/{search:segment}[/]', GET=self.get_search )
			application.add( dataserverPrefix + '/users/{user:segment}/Search/RecursiveUserGeneratedData/{term:segment}',
							 GET=self.user_search )
			return prefix + '/Search'
		return None

