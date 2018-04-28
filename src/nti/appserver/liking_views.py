#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views relating to liking and unliking objects.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid.interfaces import IRequest

from pyramid.view import view_config

from zope import component
from zope import interface

from nti.app.renderers.caching import uncached_in_response

from nti.app.renderers.decorators import AbstractTwoStateViewLinkDecorator

from nti.dataserver import authorization as nauth

from nti.dataserver import liking

from nti.dataserver.interfaces import ILikeable
from nti.dataserver.interfaces import IFavoritable

from nti.externalization.interfaces import IExternalMappingDecorator

logger = __import__('logging').getLogger(__name__)


@component.adapter(ILikeable, IRequest)
@interface.implementer(IExternalMappingDecorator)
class LikeLinkDecorator(AbstractTwoStateViewLinkDecorator):
    """
    Adds the appropriate like or unlike link.
    """
    false_view = 'like'
    true_view = 'unlike'
    link_predicate = staticmethod(liking.likes_object)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ILikeable,
             permission=nauth.ACT_READ,  # anyone that can see the object
             request_method='POST',
             name='like')
def _LikeView(request):
    """
    Given an :class:`ILikeable`, make the
    current user like the object, and return it.

    Registered as a named view, so invoked via the @@like syntax.

    """
    liking.like_object(request.context, request.authenticated_userid)
    return uncached_in_response(request.context)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=ILikeable,
             permission=nauth.ACT_READ,  # anyone that can see the object
             request_method='POST',
             name='unlike')
def _UnlikeView(request):
    """
    Given an :class:`ILikeable`, make the
    current user no longer like the object, and return it.

    Registered as a named view, so invoked via the @@unlike syntax.

    """
    liking.unlike_object(request.context, request.authenticated_userid)
    return uncached_in_response(request.context)


@interface.implementer(IExternalMappingDecorator)
@component.adapter(IFavoritable, IRequest)
class FavoriteLinkDecorator(AbstractTwoStateViewLinkDecorator):
    """
    Adds the appropriate favorite or unfavorite link.
    """

    false_view = 'favorite'
    true_view = 'unfavorite'
    link_predicate = staticmethod(liking.favorites_object)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=IFavoritable,
             permission=nauth.ACT_READ,  # anyone that can see the object
             request_method='POST',
             name='favorite')
def _FavoriteView(request):
    """
    Given an :class:`IFavoritable`, make the
    current user favorite the object, and return it.

    Registered as a named view, so invoked via the @@favorite syntax.

    """
    liking.favorite_object(request.context, request.authenticated_userid)
    return uncached_in_response(request.context)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=IFavoritable,
             permission=nauth.ACT_READ,  # anyone that can see the object
             request_method='POST',
             name='unfavorite')
def _UnfavoriteView(request):
    """
    Given an :class:`IFavoritable`, make the
    current user no longer favorite the object, and return it.

    Registered as a named view, so invoked via the @@unlike syntax.

    """
    liking.unfavorite_object(request.context, request.authenticated_userid)
    return uncached_in_response(request.context)
