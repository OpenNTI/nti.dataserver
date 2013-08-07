#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
External decorators to provide access to the things exposed through this package.

$Id: dashboard_views.py 22126 2013-08-07 16:41:55Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from pyramid.threadlocal import get_current_request

from nti.appserver.pyramid_renderers import md5_etag, _get_remote_username
from nti.appserver.forums.decorators import ForumObjectContentsLinkProvider

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.singleton import SingletonDecorator

from nti.utils._compat import aq_base

from .views import TOP_TOPICS_VIEW

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
class ForumObjectTopTopicsLinkProvider(ForumObjectContentsLinkProvider):

	__metaclass__ = SingletonDecorator

	def decorateExternalMapping(self, context, mapping):
		context = aq_base(context)
		request = get_current_request()
		if context.__parent__:
			elements = (TOP_TOPICS_VIEW, md5_etag(context.lastModified, _get_remote_username()).replace('/', '_'))
			self.add_link(TOP_TOPICS_VIEW, context, mapping, request, elements)
		else:
			logger.warn("No parent; failing to add %s link to %s", TOP_TOPICS_VIEW, context)


