#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from pyramid.security import authenticated_userid


from nti.ntiids.ntiids import is_valid_ntiid_string
from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.contentsearch import QueryObject
from nti.contentsearch.interfaces import IIndexManager
from nti.contentsearch.common import clean_search_query

import logging
logger = logging.getLogger( __name__ )

def get_collection(ntiid, default=None, registry=component):
	result = default
	if ntiid and is_valid_ntiid_string(ntiid):
		_library = registry.queryUtility( IContentPackageLibrary )
		if _library:
			paths = _library.pathToNTIID(ntiid)
			result = paths[0].ntiid if paths else default
	return unicode(result.lower()) if result else default

def _locate(obj, parent, name=None):
	# TODO: We really need to have a specific model object to represent results
	# with proper IContentTypeAware support. As it is,
	# we wind up guessing MimeType and modification info (leading to the hack below)
	# (Instead of modification info, we should be using etags here, anyway).
	# cf nti.apserver.usersearch_views._format_result
	obj.__parent__ = parent
	obj.__name__ = name
	# Sadly, these are not properly cachable
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

def get_queryobject(request):
	
	term = request.matchdict.get('term', None)
	term = clean_search_query(term)
	term = term or u''
	args = {'term': term}

	username = request.matchdict.get('user', None)
	username = username or authenticated_userid( request )
	args['username'] = username

	ntiid = request.matchdict.get('ntiid', None)
	if ntiid:
		indexid = get_collection(ntiid, default=None, registry=request.registry)
		if indexid is None:
			logger.debug("Could not find collection for ntiid '%s'" % ntiid)
		else:
			args['indexid'] = indexid

	# parse params:
	for k, v in request.params.items():
		if k in QueryObject.__properties__:
			try:
				v = v.replace(u'null', u'None')
				v = eval(v)
				v = v[0] if isinstance(v, (list, tuple)) else v
				args[k] = v
			except:
				pass
		
	return QueryObject(**args)
