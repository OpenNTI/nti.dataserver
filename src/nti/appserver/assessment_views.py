#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views related to assessment.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import pyramid.httpexceptions as hexc
from pyramid.view import view_config


from nti.dataserver.mimetype import  nti_mimetype_with_class
from nti.dataserver import authorization as nauth
from nti.ntiids import ntiids

page_info_mt = nti_mimetype_with_class( 'pageinfo' )
page_info_mt_json = page_info_mt + '+json'

####
## In pyramid 1.4, there is some minor wonkiness with the accept= request predicate.
## Your view can get called even if no Accept header is present if all the defined
## views include a non-matching accept predicate. Stil, this is much better than
## the behaviour under 1.3.
####
_view_defaults = dict( route_name='objects.generic.traversal',
					   renderer='rest',
					   context='nti.assessment.interfaces.IQuestion',
					   permission=nauth.ACT_READ,
					   request_method='GET' )
@view_config(accept=page_info_mt_json.encode('ascii'), **_view_defaults)
def pageinfo_from_question_view( request ):
	assert request.accept

	# See _question_map.
	# The __parent__ of a IQuestion we looked up by NTIID turns out to be
	# the unicode NTIID of the primary container where the question is defined.
	# However, pyramid.traversal takes a shortcut when deciding whether it needs
	# to encode the data or not: it uses `segment.__class__ is unicode` (traversal.py line 608 in 1.3.4)
	# this causes a problem if (a) the context contains non ascii characters and (b) is an instance
	# of the UnicodeContentFragment subclass of unicode: things don't get encoded. _question_map
	# has been altered to ensure that this is unicode. we also assert it here.
	__traceback_info__ =  request.context, request.context.__parent__
	assert request.context.__parent__ and request.context.__parent__.__class__ is unicode, type(request.context.__parent__)

	# XXX Assuming one location in the hierarchy, plus assuming things
	# about the filename For the sake of the application (trello #932
	# https://trello.com/c/5cxwEgVH), if the question is nested in a
	# sub-section of a content library, we want to return the PageInfo
	# for the nearest containing *physical* file. In short, this means
	# we look for an href that does not have a '#' in it.

	page_ntiid = request.context.__parent__

	content_unit = ntiids.find_object_with_ntiid( page_ntiid )
	while content_unit and '#' in getattr( content_unit, 'href', '' ):
		content_unit = getattr( content_unit, '__parent__', None )
	if content_unit:
		page_ntiid = content_unit.ntiid

	# Rather than redirecting to the canonical URL for the page, request it
	# directly. This saves a round trip, and is more compatible with broken clients that
	# don't follow redirects
	subrequest = request.blank( '/dataserver2/Objects/' + page_ntiid )
	subrequest.method = 'GET'
	subrequest.environ['REMOTE_USER'] = request.environ['REMOTE_USER']
	subrequest.environ['repoze.who.identity'] = request.environ['repoze.who.identity'].copy()
	subrequest.accept = page_info_mt_json
	return request.invoke_subrequest( subrequest )


@view_config(accept=b'application/vnd.nextthought.link+json', **_view_defaults)
def get_question_view_link( request ):
	# Not supported.
	return hexc.HTTPBadRequest()

@view_config(accept=b'', **_view_defaults) # explicit empty accept, else we get a ConfigurationConflict and/or no-Accept header goes to the wrong place
@view_config(**_view_defaults)
def get_question_view( request ):
	return request.context

del _view_defaults
