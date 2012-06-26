#!/usr/bin/env python

from __future__ import print_function, unicode_literals

from pyramid.security import authenticated_userid

from nti.contentsearch import QueryObject
from nti.contentsearch.common import get_collection
from nti.contentsearch.interfaces import IIndexManager

from nti.externalization.datastructures import LocatedExternalDict

import logging
logger = logging.getLogger( __name__ )

def _locate(obj, parent, name=None):
	obj = LocatedExternalDict( obj )
	obj.__parent__ = parent
	obj.__name__ = name
	return obj

class Search(object):

	def __init__(self, request):
		self.request = request

	def __call__( self ):
		query = get_queryobject(self.request, False, True)
		indexmanager = self.request.registry.getUtility( IIndexManager )
		return _locate( indexmanager.search( query=query, indexname=query.indexname ),
						self.request.root, 'Search' )

class ContentSearch(object):

	def __init__(self, request):
		self.request = request

	def __call__( self ):
		query = get_queryobject(self.request, True, False)
		indexmanager = self.request.registry.getUtility( IIndexManager )
		return _locate( indexmanager.content_search( query=query, indexname=query.indexname ),
						self.request.root, 'ContentSearch' )
GetSearch = ContentSearch

class UserSearch(object):

	def __init__( self, request ):
		self.request = request

	def __call__( self ):
		query = get_queryobject(self.request, False, False)
		indexmanager = self.request.registry.getUtility( IIndexManager )
		return _locate( indexmanager.user_data_search( query=query, username=query.username ),
						self.request.root, 'UserSearch' )


def clean_search_query(query):
	if query in ('*', '?'):
		return query
	return unicode(query)

def get_indexname_from_path(environ):
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

def get_queryobject(request, is_content=False, is_unified=False):
	term = request.matchdict.get('term', None)
	term = clean_search_query(term)
	term = term or ''
	args = {'term': term}

	username = request.matchdict.get('user', None)
	username = username or authenticated_userid( request )
	if username:
		args['username'] = username

	if is_content:
		indexname = get_indexname_from_path(request.environ)
		args['indexname'] = indexname
	else:
		ntiid = request.matchdict.get('ntiid', None)
		if ntiid:
			if is_unified:
				indexname = get_collection(ntiid, default=None, registry=request.registry)
				if indexname is None:
					logger.debug("Could not find collection for ntiid '%s'" % ntiid)
				args['indexname'] = indexname
			else:
				args['ntiid'] = ntiid

	return QueryObject(**args)
