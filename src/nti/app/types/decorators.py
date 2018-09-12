#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.location.interfaces import ILocation

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.appserver.pyramid_authorization import has_permission

from nti.dataserver.authorization import ACT_UPDATE

from nti.dataserver.contenttypes.forums.interfaces import ITopic

from nti.dataserver.interfaces import INote 
from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IThreadable

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalMappingDecorator

from nti.externalization.singleton import Singleton

from nti.links.links import Link

LINKS = StandardExternalFields.LINKS

logger = __import__('logging').getLogger(__name__)


@component.adapter(IUser)
@interface.implementer(IExternalMappingDecorator)
class _UserTranscriptsDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _predicate(self, context, unused_result):
        return  self._is_authenticated \
            and self.remoteUser == context

    def _do_decorate_external(self, context, result):
        links = result.setdefault(LINKS, [])
        link = Link(context, rel='transcripts', elements=('@@transcripts',))
        interface.alsoProvides(link, ILocation)
        link.__name__ = ''
        link.__parent__ = context
        links.append(link)


@component.adapter(INote)
@interface.implementer(IExternalMappingDecorator)
class _NoteRequestDecorator(AbstractAuthenticatedRequestAwareDecorator):

    @Lazy
    def _acl_decoration(self):
        result = getattr(self.request, 'acl_decoration', True)
        return result

    def _predicate(self, context, unused_result):
        return  self._acl_decoration \
            and self._is_authenticated \
            and has_permission(ACT_UPDATE, context, self.request)

    def _do_schema_link(self, context, result):
        _links = result.setdefault(LINKS, [])
        link = Link(context, rel='schema', elements=('@@schema',))
        interface.alsoProvides(link, ILocation)
        link.__name__ = ''
        link.__parent__ = context
        _links.append(link)

    def _do_decorate_external(self, context, result):
        self._do_schema_link(context, result)


@component.adapter(IThreadable)
@interface.implementer(IExternalMappingDecorator)
class _MostRecentReplyDecorator(Singleton):
    """
    Adds a link to get the most recent reply for a threadable context
    """

    def decorateExternalMapping(self, context, result):
        _links = result.setdefault(LINKS, [])
        link = Link(context,
                    rel='mostRecentReply',
                    elements=('mostRecentReply',))
        interface.alsoProvides(link, ILocation)
        link.__name__ = ''
        link.__parent__ = context
        _links.append(link)


@component.adapter(ITopic)
@interface.implementer(IExternalMappingDecorator)
class _MostRecentReplyTopicDecorator(Singleton):
    """
    Adds a link to get the most recent reply for a topic context
    """

    def decorateExternalMapping(self, context, result):
        _links = result.setdefault(LINKS, [])
        link = Link(context,
                    rel='mostRecentReply',
                    elements=('mostRecentReply',))
        interface.alsoProvides(link, ILocation)
        link.__name__ = ''
        link.__parent__ = context
        _links.append(link)
