#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views relating to liking and unliking objects.


$Id$
"""
from __future__ import print_function, unicode_literals

from pyramid.security import authenticated_userid

from pyramid.view import view_config

from zope import interface
from zope import component

from nti.appserver import _util

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import liking
from nti.dataserver import authorization as nauth

from nti.externalization import interfaces as ext_interfaces


@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(nti_interfaces.ILikeable)
class LikeLinkDecorator(_util.AbstractTwoStateViewLinkDecorator):
	"""
	Adds the appropriate like or unlike link.
	"""
	false_view = 'like'
	true_view = 'unlike'
	predicate = staticmethod(liking.likes_object)


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
	return _util.uncached_in_response( request.context )


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
	return _util.uncached_in_response( request.context )

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(nti_interfaces.IFavoritable)
class FavoriteLinkDecorator(_util.AbstractTwoStateViewLinkDecorator):
	"""
	Adds the appropriate favorite or unfavorite link.
	"""

	false_view = 'favorite'
	true_view = 'unfavorite'
	predicate = staticmethod(liking.favorites_object)


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
	return _util.uncached_in_response( request.context )

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
	return _util.uncached_in_response( request.context )
