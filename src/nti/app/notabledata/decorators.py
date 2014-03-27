#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.dataserver.interfaces import IStreamChangeEvent
from pyramid.interfaces import IRequest
from nti.externalization.interfaces import IExternalObjectDecorator
from .interfaces import IUserNotableData

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

@interface.implementer(IExternalObjectDecorator) # Because the stream externalizer doesn't call Mapping Decorator
@component.adapter(IStreamChangeEvent,IRequest)
class _StreamChangeNotableDecorator(AbstractAuthenticatedRequestAwareDecorator):
	# We expect to be used at externalization time, after everything has
	# calmed down so its safe to cache intids. however, we do need
	# to watch out for the authenticated userid from changing due to
	# delegation (when we send on a socket, for example)

	def _is_notable(self, context):
		request = self.request
		# This is really what's zope's request annotations are for
		cache = getattr(request, '_StreamChangeNotableDecorator', None)
		if cache is None:
			cache = dict()
			setattr(request, '_StreamChangeNotableDecorator', cache)
		nd = cache.get(self.authenticated_userid)
		if nd is None:
			nd = component.getMultiAdapter( (self.remoteUser, request), IUserNotableData)
			cache[self.authenticated_userid] = nd

		return nd.is_object_notable(context) or nd.is_object_notable(context.object)


	def _predicate(self, context, result):
		return self._is_authenticated and self._is_notable(context)

	def _do_decorate_external(self, context, result):
		result['RUGDByOthersThatIMightBeInterestedIn'] = True
