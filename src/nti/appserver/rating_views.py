#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views relating to rating objects.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import simplejson

from zope import interface
from zope import component

from pyramid.view import view_config
from pyramid import httpexceptions as hexc
from pyramid.security import authenticated_userid

from nti.appserver import _util

from nti.externalization import interfaces as ext_interfaces

from nti.dataserver import rating
from nti.dataserver import authorization as nauth
from nti.dataserver import interfaces as nti_interfaces

from nti.utils.maps import CaseInsensitiveDict

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(nti_interfaces.IRatable)
class RatingLinkDecorator(_util.AbstractTwoStateViewLinkDecorator):
	false_view = 'rate'
	true_view = 'unrate'
	predicate = staticmethod(rating.rates_object)

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context=nti_interfaces.IRatable,
			  permission=nauth.ACT_READ, # anyone that can see the object
			  request_method='POST',
			  name='rate')
def _RateView(request):
	data = unicode(request.body, request.charset)
	values = simplejson.loads(data) if request.body else {}
	values = CaseInsensitiveDict(**values)
	rate = values.get('rating', values.get('ranking', values.get('rate', None)))
	if rate is None:
		raise hexc.HTTPUnprocessableEntity(detail='rating not specified')

	try:
		rate = float(rate)
	except ValueError:
		raise hexc.HTTPUnprocessableEntity(detail='invaing rating')

	rating.rate_object(request.context, authenticated_userid(request), rate)
	return _util.uncached_in_response( request.context )

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context=nti_interfaces.IRatable,
			  permission=nauth.ACT_READ,
			  request_method='DELETE',
			  name='unrate')
def _RemoveRatingView(request):
	rating.unrate_object(request.context, authenticated_userid(request))
	return _util.uncached_in_response(request.context)
