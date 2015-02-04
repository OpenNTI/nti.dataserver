#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views relating to rating objects.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from . import MessageFactory as _

logger = __import__('logging').getLogger(__name__)

import simplejson

from zope import interface
from zope import component

from pyramid.view import view_config
from pyramid.interfaces import IRequest
from pyramid import httpexceptions as hexc

from nti.app.renderers.caching import uncached_in_response
from nti.app.renderers.decorators import AbstractTwoStateViewLinkDecorator

from nti.common.maps import CaseInsensitiveDict

from nti.externalization.interfaces import IExternalMappingDecorator

from nti.dataserver import authorization as nauth

from nti.dataserver import rating as ranking
from nti.dataserver.interfaces import IRatable

@interface.implementer(IExternalMappingDecorator)
@component.adapter(IRatable, IRequest)
class RatingLinkDecorator(AbstractTwoStateViewLinkDecorator):
	false_view = 'rate'
	true_view = 'unrate'
	link_predicate = staticmethod(ranking.rates_object)

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context=IRatable,
			  permission=nauth.ACT_READ, # anyone that can see the object
			  request_method='POST',
			  name='rate')
def _RateView(request):
	data = unicode(request.body, request.charset)
	values = simplejson.loads(data) if request.body else {}
	values = CaseInsensitiveDict(**values)
	rating = values.get('rating', values.get('ranking', values.get('rate', None)))
	if rating is None:
		raise hexc.HTTPUnprocessableEntity(detail= _('rating not specified'))

	try:
		rating = float(rating)
	except ValueError:
		raise hexc.HTTPUnprocessableEntity(detail= _('invaing rating'))

	ranking.rate_object(request.context, request.authenticated_userid, rating)
	return uncached_in_response( request.context )

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context=IRatable,
			  permission=nauth.ACT_READ,
			  request_method='DELETE',
			  name='unrate')
def _RemoveRatingView(request):
	ranking.unrate_object(request.context, request.authenticated_userid)
	return uncached_in_response(request.context)
