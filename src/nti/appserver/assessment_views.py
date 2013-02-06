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
## Note: In pyramid 1.3, there seems to be a bug with accept in a view config. It doesn't
## work. That or I misunderstand the documentation. So we are manually dispatching.
## The documentation also lies: wildcards are not allowed in accept= predicates;
## webob.acceptparse throws an exception (The application should offer specific types, got u'*/*') if you try (in 1.2.2)
####

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context='nti.assessment.interfaces.IQuestion',
			  permission=nauth.ACT_READ, request_method='GET',
			  accept=str(page_info_mt_json))
def pageinfo_from_question_view( request ):
	accept_type = None
	if request.accept:
		accept_type = request.accept.best_match( (page_info_mt,page_info_mt_json, b'*/*') )

	if accept_type != page_info_mt and accept_type != page_info_mt_json:
		return get_question_view( request )

	# See _question_map.
	# The __parent__ of a IQuestion we looked up by NTIID turns out to be
	# the unicode NTIID of the primary container where the question is defined.
	# However, pyramid.traversal takes a shortcut when deciding whether it needs
	# to encode the data or not: it uses `segment.__class__ is unicode` (traversal.py line 608 in 1.3.4)
	# this causes a problem if (a) the context contains non ascii characters and (b) is an instance
	# of the UnicodeContentFragment subclass of unicode: things don't get encoded. _question_map
	# has been altered to ensure that this is unicode. we also assert it here.
	__traceback_info__ = accept_type, request.context, request.context.__parent__
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

	# Using request.route_path to produce a path, not a URL, can fail when accessed over HTTPS,
	# because at some point the Location header gets turned into a full URL, and in pyramid 1.3.4,
	# this fails to take into consideration the request scheme, always return HTTP instead of HTTPS.
	# Thus we request the complete URL here (JAM: Note, this was wrong. This was a misconfiguration of
	# gunicorn/haproxy and a failure to get the secure headers.)
	# TODO: Now that we are on pyramid 1.4, consider doing this as a sub-request and skipping the redirect
	route_url = request.route_url( 'objects.generic.traversal', traverse=('NTIIDs', page_ntiid) )

	return hexc.HTTPSeeOther( location=route_url )

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context='nti.assessment.interfaces.IQuestion',
			  permission=nauth.ACT_READ, request_method='GET',
			  accept=b'application/vnd.nextthought.link+json')
def get_question_view_link( request ):
	# Not supported.
	return hexc.HTTPBadRequest()

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context='nti.assessment.interfaces.IQuestion',
			  permission=nauth.ACT_READ, request_method='GET',
			  accept=b'') # empty accept
@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context='nti.assessment.interfaces.IQuestion',
			  permission=nauth.ACT_READ, request_method='GET')
def get_question_view( request ):
	return request.context
