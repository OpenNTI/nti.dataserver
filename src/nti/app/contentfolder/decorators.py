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

from zope.location.interfaces import ILocation

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.appserver.pyramid_authorization import has_permission

from nti.contentfolder.interfaces import INamedContainer

from nti.dataserver.authorization import ACT_READ
from nti.dataserver.authorization import ACT_UPDATE

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalObjectDecorator

from nti.links.links import Link

LINKS = StandardExternalFields.LINKS

@component.adapter(INamedContainer)
@interface.implementer(IExternalObjectDecorator)
class _FolderLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):

	def _predicate(self, context, result):
		return self._is_authenticated

	def _create_link(self, context, rel, name=None):
		elements = () if not name else (name,)
		link = Link(context, rel=rel, elements=elements)
		interface.alsoProvides(link, ILocation)
		link.__name__ = ''
		link.__parent__ = context
		return link

	def _do_decorate_external(self, context, result):
		request = self.request
		_links = result.setdefault(LINKS, [])
		if has_permission(ACT_READ, context, request):
			_links.append(self._create_link(context, "contents", "@@contents"))
		if has_permission(ACT_UPDATE, context, request):
			_links.append(self._create_link(context, "mkdir", "@@mkdir"))
