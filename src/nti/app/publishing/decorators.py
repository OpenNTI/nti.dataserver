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

from zope.location.interfaces import ILocation

from pyramid.threadlocal import get_current_request

from nti.app.publishing import VIEW_PUBLISH
from nti.app.publishing import VIEW_UNPUBLISH

from nti.app.renderers.decorators import AbstractTwoStateViewLinkDecorator

from nti.appserver.pyramid_authorization import has_permission

from nti.coremetadata.interfaces import INoPublishLink

from nti.dataserver.authorization import ACT_CONTENT_EDIT

from nti.dataserver.interfaces import ICalendarPublishable

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalMappingDecorator

from nti.externalization.singleton import SingletonDecorator

from nti.links.links import Link

LINKS = StandardExternalFields.LINKS

def _acl_decoration(request):
	result = getattr(request, 'acl_decoration', True)
	return result

def _expose_links(context, request):
	return (	_acl_decoration(request)
			and	getattr(context, '_p_jar', None)
			and not INoPublishLink.providedBy(context)
			and has_permission(ACT_CONTENT_EDIT, context, request))

def _get_publish_state(obj):
	return 'DefaultPublished' if obj.is_published() else None

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

	def _do_decorate_external_link(self, context, mapping, extra_elements=()):
		# ICalendarPublishables have their own publish link decorator.
		if 		_expose_links(context, self.request) \
			and not ICalendarPublishable.providedBy(context):
			super(PublishLinkDecorator, self)._do_decorate_external_link(context, mapping)

	def _do_decorate_external(self, context, mapping):
		super(PublishLinkDecorator, self)._do_decorate_external(context, mapping)
		# Everyone gets the status
		if 'PublicationState' not in mapping:
			mapping['PublicationState'] = _get_publish_state(context)

@interface.implementer(IExternalMappingDecorator)
class CalendarPublishStateDecorator(object):
	"""
	Adds both the `publish` and `unpublish` links to our outbound object.

	Since `ICalendarPublishable` objects have three possible states, the
	client may call any of these links from any state.
	"""
	__metaclass__ = SingletonDecorator

	def decorateExternalMapping(self, context, result):
		request = get_current_request()
		if _expose_links(context, request):
			_links = result.setdefault(LINKS, [])
			for rel in (VIEW_PUBLISH, VIEW_UNPUBLISH):
				el = '@@%s' % rel
				link = Link(context, rel=rel, elements=(el,))
				interface.alsoProvides(link, ILocation)
				link.__name__ = ''
				link.__parent__ = context
				_links.append(link)
		result['publishEnding'] = context.publishEnding
		result['publishBeginning'] = context.publishBeginning
		result['PublicationState'] = _get_publish_state(context)
