#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.dataserver.interfaces import IUser
from nti.appserver.interfaces import IAuthenticatedUserLinkProvider

from pyramid.view import view_config

from nti.appserver import httpexceptions as hexc
from .link_provider import VIEW_NAME_NAMED_LINKS

def _find_link_provider( user, request, link_name ):

	for provider in component.subscribers( (user, request), IAuthenticatedUserLinkProvider ):
		if getattr( provider, '__name__', '' ) == link_name:
			return provider

@view_config( name=VIEW_NAME_NAMED_LINKS,
			  route_name='objects.generic.traversal',
			  request_method='GET',
			  permission=nauth.ACT_READ,
			  context=IUser )
def named_link_get_view( request ):
	if not len(request.subpath) == 1: # exactly one subpath, the link name
		return hexc.HTTPNotFound()
	provider = _find_link_provider( request.context, request, request.subpath[0] )
	if provider is None:
		return hexc.HTTPNotFound()
	# TODO: If it's a conditional link provider, and it's not going to provide a link,
	# should we 404?
	return hexc.HTTPNoContent() if not provider.url else hexc.HTTPSeeOther( provider.url )

@view_config( name=VIEW_NAME_NAMED_LINKS,
			  route_name='objects.generic.traversal',
			  request_method='DELETE',
			  permission=nauth.ACT_DELETE,
			  context=IUser )
def named_link_delete_view( request ):
	if not len(request.subpath) == 1: # exactly one subpath, the link name
		return hexc.HTTPNotFound()
	provider = _find_link_provider( request.context, request, request.subpath[0] )
	if provider is None:
		return hexc.HTTPNotFound()

	if not getattr( provider, 'minGeneration', None ):
		return hexc.HTTPForbidden() # Not a conditional, thus cannot be deleted

	# This counts as having taken the action.
	provider.match_generation()
	return hexc.HTTPNoContent()
