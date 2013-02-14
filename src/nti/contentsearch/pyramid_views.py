# -*- coding: utf-8 -*-
"""
Search pyramid views.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import

logger = __import__( 'logging' ).getLogger( __name__ )

import re

from zope import interface
from zope.location import locate

from pyramid.security import authenticated_userid

from .interfaces import IIndexManager
from ._search_query import QueryObject
from ._views_utils import get_collection
from ._content_utils import get_content_translation_table

def _locate(obj, parent, name=None):
	# TODO: (Instead of modification info, we should be using etags here, anyway).
	locate(obj, parent, name)
	# TODO: Make cachable?
	from nti.appserver import interfaces as app_interfaces # Avoid circular imports
	interface.alsoProvides( obj, app_interfaces.IUncacheableInResponse )
	
	return obj

class Search(object):

	def __init__(self, request):
		self.request = request

	def __call__( self ):
		query = get_queryobject(self.request)
		indexmanager = self.request.registry.getUtility( IIndexManager )
		return _locate( indexmanager.search( query=query), self.request.root, 'Search' )

class UserSearch(object):

	def __init__( self, request ):
		self.request = request

	def __call__( self ):
		query = get_queryobject(self.request)
		indexmanager = self.request.registry.getUtility( IIndexManager )
		return _locate( indexmanager.user_data_search( query=query ), self.request.root, 'UserSearch' )

_extractor_pe = re.compile('[?*]*(.*)')

def clean_search_query(query, language='en'):
	temp = re.sub('[*?]','', query)
	result = unicode(query) if temp else u''
	if result:
		m = _extractor_pe.search(result)
		result = m.group() if m else u''
	
	table = get_content_translation_table(language)
	result = result.translate(table) if result else u''
	return unicode(result)

def get_queryobject(request):
	
	# parse params:
	args = dict(request.params)
	
	term = request.matchdict.get('term', u'')
	term = clean_search_query(unicode(term))
	args['term'] =  term

	username = request.matchdict.get('user', None)
	username = username or authenticated_userid( request )
	args['username'] = username

	ntiid = request.matchdict.get('ntiid', None)
	searchOn = request.matchdict.get('searchOn', None)
	if ntiid:
		args['location'] = ntiid
		indexid = get_collection(ntiid, request.registry)
		if indexid is None:
			logger.debug("Could not find collection for ntiid '%s'" % ntiid)
		else:
			args['indexid'] = indexid
	elif searchOn:
		nset = set()
		for ntiid in searchOn.split(','):
			ntiid = get_collection(ntiid, request.registry)
			if ntiid is None:
				logger.debug("Could not find collection for ntiid '%s'" % ntiid)
			else:
				nset.add(ntiid)
		if nset:
			args['searchOn'] = nset
			
	# from IPython.core.debugger import Tracer;  Tracer()() 
	return QueryObject(**args)
