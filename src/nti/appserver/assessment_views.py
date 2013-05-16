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

from nti.dataserver import authorization as nauth

from .contentlibrary_views import find_page_info_view_helper
from .contentlibrary_views import PAGE_INFO_MT_JSON

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
@view_config(accept=PAGE_INFO_MT_JSON.encode('ascii'), **_view_defaults)
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

	page_ntiid = request.context.__parent__
	return find_page_info_view_helper( request, page_ntiid )


@view_config(accept=b'application/vnd.nextthought.link+json', **_view_defaults)
def get_question_view_link( request ):
	# Not supported.
	return hexc.HTTPBadRequest()

@view_config(accept=b'', **_view_defaults) # explicit empty accept, else we get a ConfigurationConflict and/or no-Accept header goes to the wrong place
@view_config(**_view_defaults)
def get_question_view( request ):
	return request.context

del _view_defaults
