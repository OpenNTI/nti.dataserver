#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from pyramid.view import view_config

from nti.appserver import httpexceptions as hexc

from nti.dataserver.interfaces import IUser

from nti.dataserver import authorization as nauth

from . import safe_links
from . import unique_link_providers

from .link_provider import VIEW_NAME_NAMED_LINKS

def _find_link_providers( user, request, link_name ):
	unique_providers = []
	for provider in unique_link_providers( user, request ):
		rels = set()
		rels.add(getattr(provider ,'rel', None))
		rels.update(getattr(provider ,'rels', ()))
		rels.add(getattr(provider ,'__name__', None))
		rels.discard(None)
		unique_providers.append((rels, getattr(provider, 'priority', 0), provider))
		
	providers = []
	ignored = set()
	for rels, _, provider in sorted(unique_providers, reverse=True):
		try:
			provider_links = provider.get_links() 
		except NotImplementedError:
			ignored.update(rels or ())
		else:
			name = getattr(provider, '__name__', '')
			if name == link_name and name not in ignored:
				providers.append( provider )
			elif any((x for x in provider_links if x.rel == link_name)) and \
				 not any((x for x in provider_links if x.rel in ignored)):
				providers.append( provider )
	return providers

def _preflight( request ):
	if not len(request.subpath) == 1: # exactly one subpath, the link name
		return hexc.HTTPNotFound(), None, None
	
	link_name = request.subpath[0]
	providers = _find_link_providers( request.context, request, link_name )
	if len(providers) != 1: # Too many matches, what to do?
		return hexc.HTTPNotFound("Too many links: " + str(len(providers))), None, None
	
	# If it's a conditional link provider, and it's not going to provide a link,
	# we 404, maintaining the illusion of deletion
	provider = providers[0]
	if not any( (x for x in safe_links(provider) if x.rel == link_name) ): # Conditional that's been un-conditioned
		return hexc.HTTPNotFound(), None, None

	return None, provider, link_name

@view_config( name=VIEW_NAME_NAMED_LINKS,
			  route_name='objects.generic.traversal',
			  request_method='GET',
			  permission=nauth.ACT_READ,
			  context=IUser )
def named_link_get_view( request ):
	rsp, provider, _ = _preflight( request )
	if rsp:
		return rsp # response

	# If the URL is not absolute already, then when the request is written out it will be
	# made so by pyramid.
	return hexc.HTTPNoContent() if not provider.url else hexc.HTTPSeeOther( provider.url )

@view_config( name=VIEW_NAME_NAMED_LINKS,
			  route_name='objects.generic.traversal',
			  request_method='DELETE',
			  permission=nauth.ACT_DELETE,
			  context=IUser )
def named_link_delete_view( request ):
	rsp, provider, link_name = _preflight( request )
	if rsp:
		return rsp

	if not getattr( provider, 'delete_link', None ):
		return hexc.HTTPMethodNotAllowed() # Not a conditional, thus cannot be deleted

	# This counts as having taken the action.
	provider.delete_link( link_name )
	return hexc.HTTPNoContent()
