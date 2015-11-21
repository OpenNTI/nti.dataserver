#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views related to publishing.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from abc import ABCMeta, abstractmethod

from datetime import datetime

from pyramid.view import view_config
from pyramid.view import view_defaults  # NOTE: Only usable on classes

from nti.app.externalization.internalization import read_body_as_external_object

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.renderers.caching import uncached_in_response

from nti.common.maps import CaseInsensitiveDict

from nti.dataserver import authorization as nauth
from nti.dataserver.interfaces import IPublishable
from nti.dataserver.interfaces import IDefaultPublished
from nti.dataserver.interfaces import ICalendarPublishable

from . import VIEW_PUBLISH
from . import VIEW_UNPUBLISH

class _AbstractPublishingView(object):
	__metaclass__ = ABCMeta

	_iface = IDefaultPublished

	def __init__(self, request):
		self.request = request

	@abstractmethod
	def _do_provide(self, topic):
		"""
		This method is responsible for firing any ObjectSharingModifiedEvents needed.
		"""
		# Which is done by the topic object's publish/unpublish method
		raise NotImplementedError()  # pragma: no cover

	@abstractmethod
	def _test_provides(self, topic):
		raise NotImplementedError()  # pragma: no cover

	def __call__(self):
		request = self.request
		topic = request.context

		if not IPublishable.providedBy(topic):
			raise TypeError("Object not publishable; this is a development error.",
							topic)

		if self._test_provides(topic):
			self._do_provide(topic)

		request.response.location = request.resource_path(topic)
		return uncached_in_response(topic)

@view_config(context=IPublishable)
@view_defaults(route_name='objects.generic.traversal',
				renderer='rest',
				permission=nauth.ACT_UPDATE,
				request_method='POST',
				name=VIEW_PUBLISH)
class PublishView(_AbstractPublishingView):

	def _do_provide(self, topic):
		topic.publish()

	def _test_provides(self, topic):
		return not IDefaultPublished.providedBy(topic)

@view_config(context=IPublishable)
@view_defaults(route_name='objects.generic.traversal',
				renderer='rest',
				permission=nauth.ACT_UPDATE,
				request_method='POST',
				name=VIEW_UNPUBLISH)
class UnpublishView(_AbstractPublishingView):

	def _do_provide(self, topic):
		topic.unpublish()

	def _test_provides(self, topic):
		return IDefaultPublished.providedBy(topic)

@view_config(context=ICalendarPublishable)
@view_defaults(route_name='objects.generic.traversal',
				renderer='rest',
				permission=nauth.ACT_UPDATE,
				request_method='POST',
				name=VIEW_PUBLISH)
class CalendarPublishView(_AbstractPublishingView, ModeledContentUploadRequestUtilsMixin):
	"""
	For calendar publishables, we provide links at all times. With three
	states (published, date-bound published, and unpublished), we
	must handle calls that may or may not make sense.
	"""

	def _to_date(self, timestamp):
		timestamp = int( timestamp )
		return datetime.utcfromtimestamp( timestamp )

	def _get_dates(self):
		start = end = None
		if self.request.body:
			values = read_body_as_external_object(self.request)
			values = CaseInsensitiveDict( values )
			start = values.get('publishBeginning', None)
			end = values.get('publishEnding', None)
			if start:
				start = self._to_date( start )
			if end:
				end = self._to_date( end )
		return start, end

	def _do_provide(self, obj):
		start, end = self._get_dates()
		obj.publish( start=start, end=end )

	def _test_provides(self, topic):
		# Allow the underlying implementation to handle state.
		return True

@view_config(context=ICalendarPublishable)
@view_defaults(route_name='objects.generic.traversal',
				renderer='rest',
				permission=nauth.ACT_UPDATE,
				request_method='POST',
				name=VIEW_UNPUBLISH)
class CalendarUnpublishView(_AbstractPublishingView):

	def _do_provide(self, topic):
		topic.unpublish()

	def _test_provides(self, topic):
		# Allow the underlying implementation to handle state.
		return True
