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
from zope.location.interfaces import ILocation

from pyramid.view import view_config
from pyramid import httpexceptions as hexc
from pyramid.security import authenticated_userid
from pyramid.threadlocal import get_current_request

from nti.appserver import _util

from nti.externalization import oids as ext_oids
from nti.externalization.singleton import SingletonDecorator
from nti.externalization import interfaces as ext_interfaces
from nti.externalization.interfaces import StandardExternalFields

from nti.dataserver import links
from nti.dataserver import ratings
from nti.dataserver import authorization as nauth
from nti.dataserver import interfaces as nti_interfaces

from nti.utils.maps import CaseInsensitiveDict

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(nti_interfaces.IRatable)
class RatingLinkDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalMapping(self, context, mapping, extra_elements=()):
		request = get_current_request()
		current_username = authenticated_userid(request) if request else None
		if not current_username or not context.__parent__:
			return

		target_ntiid = ext_oids.to_external_ntiid_oid(context)
		if target_ntiid is None:
			logger.warn("Failed to get ntiid; not adding rating links for %s", context)
			return

		data = (("rate", "POST"), ('unrate', 'DELETE'))
		_links = mapping.setdefault(StandardExternalFields.LINKS, [])
		for rel, method in data:
			link = links.Link(target_ntiid, rel=rel, method=method,
							  elements=('@@' + rel,) + extra_elements)
			interface.alsoProvides(link, ILocation)
			link.__name__ = ''
			link.__parent__ = context
			_links.append(link)

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context=nti_interfaces.IRatable,
			  permission=nauth.ACT_READ, # anyone that can see the object
			  request_method='POST',
			  name='like')
def _RateView(request):
	data = unicode(request.body, request.charset)
	values = simplejson.loads(data) if request.body else {}
	values = CaseInsensitiveDict(**values)
	rate = values.get('rating', values.get('rate', None))
	if rate is None:
		raise hexc.HTTPUnprocessableEntity(detail='rating not specified')

	try:
		rate = float(rate)
	except ValueError:
		raise hexc.HTTPUnprocessableEntity(detail='invaing rating')

	ratings.rate_object(request.context, authenticated_userid(request), rate)
	return _util.uncached_in_response( request.context )

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context=nti_interfaces.IRatable,
			  permission=nauth.ACT_READ,
			  request_method='DELETE',
			  name='unlike')
def _RemoveRatingView(request):
	ratings.unrate_object(request.context, authenticated_userid(request))
	return _util.uncached_in_response(request.context)
