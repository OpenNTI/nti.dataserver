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

from nti.app.publishing import VIEW_PUBLISH
from nti.app.publishing import VIEW_UNPUBLISH

from nti.app.renderers.decorators import AbstractTwoStateViewLinkDecorator

from nti.appserver.pyramid_authorization import has_permission

from nti.dataserver.authorization import ACT_CONTENT_EDIT

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalMappingDecorator

LINKS = StandardExternalFields.LINKS

@interface.implementer(IExternalMappingDecorator)
class PublishLinkDecorator(AbstractTwoStateViewLinkDecorator):
	"""
	Adds the appropriate publish or unpublish link for the owner
	of the object.

	Also, because that information is useful to have for others to
	which the post is visible (for cases where additional permissions
	beyond default published are in use; in that case, visibility
	doesn't necessarily imply publication), we also provide a
	``PublicationState`` containing one of the values
	``DefaultPublished`` or null.
	"""
	false_view = VIEW_PUBLISH
	true_view = VIEW_UNPUBLISH

	def link_predicate(self, context, current_username):
		return context.is_published()

	def _expose_links(self, context):
		return 	getattr(context, '_p_jar', None) \
 			and has_permission(ACT_CONTENT_EDIT, context, self.request)

	def _do_decorate_external_link(self, context, mapping, extra_elements=()):
		if self._expose_links( context ):
			super(PublishLinkDecorator, self)._do_decorate_external_link(context, mapping)

	def _do_decorate_external(self, context, mapping):
		super(PublishLinkDecorator, self)._do_decorate_external(context, mapping)
		# Everyone gets the status
		mapping['PublicationState'] = 'DefaultPublished' \
									  if context.is_published() else None
