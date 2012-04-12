import re
from pyramid.security import authenticated_userid

from nti.contentsearch import QueryObject
from nti.contentsearch.interfaces import IIndexManager

import logging
logger = logging.getLogger( __name__ )

# -----------------------------

class GetSearch(object):

	def __init__(self, request):
		self.request = request

	def __call__( self ):
		query = get_queryobject(self.request)
		indexmanager = self.request.registry.getUtility( IIndexManager )
		return indexmanager.content_search( query=query, indexname=query.indexname )

class UserSearch(object):

	def __init__( self, request ):
		self.request = request

	def __call__( self ):
		query = get_queryobject(self.request, False)
		indexmanager = self.request.registry.getUtility( IIndexManager )
		return indexmanager.user_data_search( query=query, username=query.username )
	
# -----------------------------

def clean_search_query(query):
	if query in ('*', '?'):
		return query
	result = re.sub('[*?]', '', query) if query else u''
	return unicode(result.lower())

def get_indexname(environ):
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

def get_queryobject(request, get_index=True):
	
	term = request.matchdict.get('term', None)
	term = clean_search_query(term)
	args = {'term': term}
		
	username = request.matchdict.get('user', None)
	username = username or authenticated_userid( request )
	if username:
		args['username'] = username
		
	if get_index:
		args['indexname'] = get_indexname(request.environ)
	
	return QueryObject(**args)
	