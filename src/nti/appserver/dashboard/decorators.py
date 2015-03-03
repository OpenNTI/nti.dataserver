#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
External decorators to provide access to the things exposed through this package.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope.container.interfaces import ILocation

from nti.app.renderers.caching import md5_etag
from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.externalization import interfaces as ext_interfaces

from nti.links.links import Link

from nti.utils._compat import aq_base

from .views import TOP_TOPICS_VIEW

# These imports are broken out explicitly for speed (avoid runtime attribute lookup)
LINKS = ext_interfaces.StandardExternalFields.LINKS

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
class ForumObjectTopTopicsLinkProvider(AbstractAuthenticatedRequestAwareDecorator):

	@classmethod
	def add_link(cls, rel, context, mapping, request, elements):
		_links = mapping.setdefault(LINKS, [])
		link = Link(context, rel=rel, elements=elements)
		interface.alsoProvides(link, ILocation)
		link.__name__ = ''
		link.__parent__ = context
		_links.append(link)
		return link

	def _predicate(self, context, result):
		return self._is_authenticated and aq_base(context).__parent__ is not None

	def _do_decorate_external(self, context, mapping):
		context = aq_base(context)
		userid = self.authenticated_userid
		elements = (TOP_TOPICS_VIEW, md5_etag(context.lastModified, userid).replace('/', '_'))
		self.add_link(TOP_TOPICS_VIEW, context, mapping, self.request, elements)
