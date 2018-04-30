#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views relating to rating objects.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid import httpexceptions as hexc

from pyramid.interfaces import IRequest

from pyramid.view import view_config

from requests.structures import CaseInsensitiveDict

import simplejson

from zope import interface
from zope import component

from nti.app.renderers.caching import uncached_in_response

from nti.app.renderers.decorators import AbstractTwoStateViewLinkDecorator

from nti.app.externalization.error import raise_json_error

from nti.appserver import MessageFactory as _

from nti.base._compat import text_

from nti.externalization.interfaces import IExternalMappingDecorator

from nti.dataserver import authorization as nauth

from nti.dataserver import rating as ranking

from nti.dataserver.interfaces import IRatable

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IExternalMappingDecorator)
@component.adapter(IRatable, IRequest)
class RatingLinkDecorator(AbstractTwoStateViewLinkDecorator):
    false_view = 'rate'
    true_view = 'unrate'
    link_predicate = staticmethod(ranking.rates_object)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=IRatable,
             permission=nauth.ACT_READ,  # anyone that can see the object
             request_method='POST',
             name='rate')
def _RateView(request):
    data = text_(request.body, request.charset)
    values = simplejson.loads(data) if request.body else {}
    values = CaseInsensitiveDict(**values)
    rating = values.get('rate', None) \
          or values.get('rating', None) \
          or values.get('ranking', None)
    if rating is None:
        raise_json_error(request,
                         hexc.HTTPUnprocessableEntity,
                         {
                             'message': _(u'Rating not specified.'),
                             'code': 'RatingMissing',
                         },
                         None)

    try:
        rating = float(rating)
    except ValueError:
        raise_json_error(request,
                         hexc.HTTPUnprocessableEntity,
                         {
                             'message': _(u'Invalid rating.'),
                             'code': 'Invalid Rating',
                         },
                         None)

    ranking.rate_object(request.context, request.authenticated_userid, rating)
    return uncached_in_response(request.context)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=IRatable,
             permission=nauth.ACT_READ,
             request_method='DELETE',
             name='unrate')
def _RemoveRatingView(request):
    ranking.unrate_object(request.context, request.authenticated_userid)
    return uncached_in_response(request.context)
