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

from zope.intid.interfaces import IIntIds

from pyramid.interfaces import IRequest

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.dataserver.interfaces import IStreamChangeEvent
from nti.dataserver.interfaces import get_notable_filter

from nti.externalization.interfaces import IExternalObjectDecorator

@interface.implementer(IExternalObjectDecorator)  # Because the stream externalizer doesn't call Mapping Decorator
@component.adapter(IStreamChangeEvent, IRequest)
class _StreamChangeNotableDecorator(AbstractAuthenticatedRequestAwareDecorator):
	# We expect to be used at externalization time, after everything has
	# calmed down so its safe to cache intids. however, we do need
	# to watch out for the authenticated userid from changing due to
	# delegation (when we send on a socket, for example)

	def _is_notable(self, context):
		# In local timings,
		# the legacy method of checking if the give context id is in
		# our notable set is about 100x slower when we do not have a
		# cache in play (either we do not have a cache object or our
		# cache has been invalidated).  As expected, when we do have a cache,
		# it is about 100x faster than running our object through the algorithm.
		result = False
		intids = component.getUtility(IIntIds)
		# Check if this object is persistent first
		if 		intids.queryId(context) is not None \
			or	intids.queryId(context.object) is not None:
			# TODO: We may have to pass the request to INotableFilter
			is_notable_ctx = get_notable_filter(context)
			is_notable_obj = get_notable_filter(context.object)
			result = is_notable_ctx(self.remoteUser) or is_notable_obj(self.remoteUser)
		return result

	def _predicate(self, context, result):
		return self._is_authenticated and self._is_notable(context)

	def _do_decorate_external(self, context, result):
		result['RUGDByOthersThatIMightBeInterestedIn'] = True
