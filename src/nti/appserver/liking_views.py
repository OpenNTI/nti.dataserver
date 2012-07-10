#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views relating to liking and unliking objects.


$Id$
"""
from __future__ import print_function, unicode_literals



from pyramid.security import authenticated_userid
from pyramid.threadlocal import get_current_request

from pyramid.view import view_config

from zope import interface
from zope import component
from zope.location.interfaces import ILocation

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import liking
from nti.dataserver import links
from nti.dataserver import authorization as nauth

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.interfaces import StandardExternalFields


@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(nti_interfaces.ILikeable)
class LikeLinkDecorator(object):
	"""
	Adds the appropriate like or unlike link.
	"""
	def __init__( self, ctx ): pass

	def decorateExternalMapping( self, context, mapping ):
		current_user = authenticated_userid( get_current_request() )
		if not current_user:
			return

		i_like = liking.likes_object( context, current_user )
		_links = mapping.setdefault( StandardExternalFields.LINKS, [] )
		# We're assuming that because you can see it, you can (un)like it.
		# this matches the views
		rel = 'unlike' if i_like else 'like'
		link = links.Link( context, rel=rel, elements=('@@' + rel,) )
		interface.alsoProvides( link, ILocation )
		link.__name__ = ''
		link.__parent__ = context
		_links.append( link )


@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context=nti_interfaces.ILikeable,
			  permission=nauth.ACT_READ, # anyone logged in...
			  request_method='POST',
			  name='like')
def _LikeView(request):
	"""
	Given an :class:`nti_interfaces.ILikeable`, make the
	current user like the object, and return it.

	Registered as a named view, so invoked via the @@like syntax.

	"""

	liking.like_object( request.context, authenticated_userid( request ) )
	return request.context


@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context=nti_interfaces.ILikeable,
			  permission=nauth.ACT_READ, # anyone logged in...
			  request_method='POST',
			  name='unlike')
def _UnlikeView(request):
	"""
	Given an :class:`nti_interfaces.ILikeable`, make the
	current user no longer like the object, and return it.

	Registered as a named view, so invoked via the @@unlike syntax.

	"""

	liking.unlike_object( request.context, authenticated_userid( request ) )
	return request.context
