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

	route_path = request.route_path( 'objects.generic.traversal', traverse=('NTIIDs',request.context.__parent__) )
	return hexc.HTTPSeeOther( location=route_path )

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
