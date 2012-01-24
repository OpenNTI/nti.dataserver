from nti.contentsearch.interfaces import IIndexManager

# TODO: We should make this a config option
USE_TYPE_AHEAD = False

class GetSearch(object):

	def __init__(self, request):
		self.request = request

	def __call__( self ):
		request = self.request
		indexmanager = request.registry.getUtility( IIndexManager )

		query = self.request.matchdict['term']
		indexname = self.get_indexname(self.request.environ)

		search = indexmanager.quick_search if USE_TYPE_AHEAD else indexmanager.search
		return search( query=query, indexname=indexname )

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

class UserSearch(object):

	def __init__( self, request ):
		self.request = request

	def __call__( self ):
		term = self.request.matchdict['term']
		user = self.request.matchdict['user']
		indexmanager = self.request.registry.getUtility( IIndexManager )

		return indexmanager.user_data_search( term, username=user )
