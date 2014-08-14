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

from pyramid.view import view_config
from pyramid.view import view_defaults  # NOTE: Only usable on classes

from nti.app.renderers.caching import uncached_in_response

from nti.dataserver import authorization as nauth

from nti.dataserver import interfaces as nti_interfaces


from . import VIEW_PUBLISH
from . import VIEW_UNPUBLISH


class _AbstractPublishingView(object):
	__metaclass__ = ABCMeta

	_iface = nti_interfaces.IDefaultPublished

	def __init__( self, request ):
		self.request = request

	@abstractmethod
	def _do_provide(self, topic):
		"""This method is responsible for firing any ObjectSharingModifiedEvents needed."""
		# Which is done by the topic object's publish/unpublish method
		raise NotImplementedError() # pragma: no cover
	@abstractmethod
	def _test_provides(self, topic):
		raise NotImplementedError() # pragma: no cover

	def __call__(self):
		request = self.request
		topic = request.context

		if not nti_interfaces.IPublishable.providedBy(topic):
			raise TypeError("Object not publishable; this is a development error.",
							topic)

		if self._test_provides( topic ):
			self._do_provide( topic )

		request.response.location = request.resource_path( topic )
		return uncached_in_response( topic )

@view_config( context=nti_interfaces.IPublishable )
@view_defaults( route_name='objects.generic.traversal',
				renderer='rest',
				permission=nauth.ACT_UPDATE,
				request_method='POST',
				name=VIEW_PUBLISH )
class PublishView(_AbstractPublishingView):
	def _do_provide( self, topic ):
		topic.publish()
	def _test_provides( self, topic ):
		return not nti_interfaces.IDefaultPublished.providedBy( topic )

@view_config( context=nti_interfaces.IPublishable )
@view_defaults( route_name='objects.generic.traversal',
				renderer='rest',
				permission=nauth.ACT_UPDATE,
				request_method='POST',
				name=VIEW_UNPUBLISH )
class UnpublishView(_AbstractPublishingView):
	def _do_provide( self, topic ):
		topic.unpublish()
	def _test_provides( self, topic ):
		return nti_interfaces.IDefaultPublished.providedBy( topic )
