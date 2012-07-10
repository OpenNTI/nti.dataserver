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

class _AbstractLikeLinkDecorator(object):
	"""
	Adds the appropriate like or unlike link.

	.. note:: This causes the returned objects to be user-specific,
		which may screw with caching.
	"""

	like_view = 'like'
	unlike_view = 'unlike'

	likes_predicate = staticmethod(liking.likes_object)

	def __init__( self, ctx ): pass

	def decorateExternalMapping( self, context, mapping ):
		current_user = authenticated_userid( get_current_request() )
		if not current_user:
			return

		# We only do this for parented objects. Otherwise, we won't
		# be able to render the links. A non-parented object is usually
		# a weakref to an object that has been left around
		# in somebody's stream
		if not context.__parent__:
			return

		i_like = self.likes_predicate( context, current_user )
		_links = mapping.setdefault( StandardExternalFields.LINKS, [] )
		# We're assuming that because you can see it, you can (un)like it.
		# this matches the views
		rel = self.unlike_view if i_like else self.like_view
		link = links.Link( context, rel=rel, elements=('@@' + rel,) )
		interface.alsoProvides( link, ILocation )
		link.__name__ = ''
		link.__parent__ = context
		_links.append( link )


@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(nti_interfaces.ILikeable)
class LikeLinkDecorator(_AbstractLikeLinkDecorator):
	"""
	Adds the appropriate like or unlike link.
	"""


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


@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(nti_interfaces.IFavoritable)
class FavoriteLinkDecorator(_AbstractLikeLinkDecorator):
	"""
	Adds the appropriate favorite or unfavorite link.
	"""

	like_view = 'favorite'
	unlike_view = 'unfavorite'
	likes_predicate = staticmethod(liking.favorites_object)


@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context=nti_interfaces.IFavoritable,
			  permission=nauth.ACT_READ, # anyone logged in...
			  request_method='POST',
			  name='favorite')
def _FavoriteView(request):
	"""
	Given an :class:`nti_interfaces.IFavoritable`, make the
	current user favorite the object, and return it.

	Registered as a named view, so invoked via the @@favorite syntax.

	"""

	liking.favorite_object( request.context, authenticated_userid( request ) )
	return request.context


@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context=nti_interfaces.IFavoritable,
			  permission=nauth.ACT_READ, # anyone logged in...
			  request_method='POST',
			  name='unfavorite')
def _UnfavoriteView(request):
	"""
	Given an :class:`nti_interfaces.IFavoritable`, make the
	current user no longer favorite the object, and return it.

	Registered as a named view, so invoked via the @@unlike syntax.

	"""

	liking.unfavorite_object( request.context, authenticated_userid( request ) )
	return request.context
