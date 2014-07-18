#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.i18nmessageid
MessageFactory = zope.i18nmessageid.MessageFactory('nti.dataserver')

from zope import component
from nti.appserver.interfaces import IAuthenticatedUserLinkProvider

def safe_links(provider):
	try:
		return provider.get_links()
	except NotImplementedError:
		return ()
	
def unique_link_providers(user,request):
	"""
	Given a user and the request, find and return all the link
	providers for that user.

	This takes into account the site hierarchy, allowing sub-site configurations
	to override the base configuration based on matching rel.

	:return: An iterable of link objects.
	"""

	seen_names = set()
	# Subscribers are returned in REVERSE order, that is, from
	# all the bases FIRST...so to let the lower levels win, we reverse again
	# not pyramid.threadlocal.get_current_registry or request.registry, it ignores the site
	for provider in reversed(component.subscribers( (user,request), IAuthenticatedUserLinkProvider )):
		# Our objects have a __name__ and they only produce one link
		name = getattr(provider, '__name__', None)
		if name:
			if name in seen_names:
				continue
			seen_names.add(name)
			yield provider
		else:
			yield provider

def provide_links(user, request):
	"""
	Given a user and the request, find and provide all the links
	for that user.

	This takes into account the site hierarchy, allowing sub-site configurations
	to override the base configuration based on matching rel.

	:return: An iterable of link objects.
	"""

	seen_rels = set()
	for provider in unique_link_providers(user,request):
		for link in safe_links(provider):
			if link.rel in seen_rels:
				# In the case of our objects, of course, rel is the same
				# as the name configured in ZCML, and we only provide one link
				continue
			seen_rels.add( link.rel )
			yield link
