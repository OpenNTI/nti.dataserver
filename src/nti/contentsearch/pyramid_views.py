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
from zope.mimetype import interfaces as zmime_interfaces

from pyramid.security import authenticated_userid


from nti.ntiids.ntiids import is_valid_ntiid_string
from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.contentsearch import QueryObject
from nti.contentsearch.interfaces import IIndexManager

from nti.externalization.datastructures import LocatedExternalDict

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
	# with proper IExternalObject and IContentTypeAware support. As it is,
	# we wind up guessing MimeType and modification info (leading to the hack below)
	# (Instead of modification info, we should be using etags here, anyway).
	# cf nti.apserver.usersearch_views._format_result
	obj = LocatedExternalDict( obj )
	obj.__parent__ = parent
	obj.__name__ = name
	# Sadly, these are not properly cachable
	from nti.appserver import interfaces as app_interfaces # Avoid circular imports
	from nti.dataserver import mimetype as nti_mimetype

	interface.alsoProvides( obj, app_interfaces.IUncacheableInResponse )
	interface.alsoProvides( obj, zmime_interfaces.IContentTypeAware )
	obj.mime_type = nti_mimetype.nti_mimetype_with_class( None )
	return obj

class Search(object):

	def __init__(self, request):
		self.request = request

	def __call__( self ):
		query = get_queryobject(self.request)
		indexmanager = self.request.registry.getUtility( IIndexManager )
		return _locate( indexmanager.search( query=query, indexid=query.indexid ),
						self.request.root, 'Search' )

class UserSearch(object):

	def __init__( self, request ):
		self.request = request

	def __call__( self ):
		query = get_queryobject(self.request)
		indexmanager = self.request.registry.getUtility( IIndexManager )
		return _locate( indexmanager.user_data_search( query=query, username=query.username ),
						self.request.root, 'UserSearch' )

def clean_search_query(query):
	temp = query.replace('*', '')
	temp = temp.replace('?', '')
	if not temp:
		return None
	return unicode(query)

def get_queryobject(request):
	term = request.matchdict.get('term', None)
	term = clean_search_query(term)
	term = term or ''
	args = {'term': term}

	username = request.matchdict.get('user', None)
	username = username or authenticated_userid( request )
	if username:
		args['username'] = username

	ntiid = request.matchdict.get('ntiid', None)
	if ntiid:
		indexid = get_collection(ntiid, default=None, registry=request.registry)
		if indexid is None:
			logger.debug("Could not find collection for ntiid '%s'" % ntiid)
		else:
			args['indexid'] = indexid

	return QueryObject(**args)
