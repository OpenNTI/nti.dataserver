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

from nti.dataserver.authorization import ACT_UPDATE

from nti.dataserver.interfaces import INote
from nti.dataserver.interfaces import IThreadable
from nti.dataserver.contenttypes.forums.interfaces import ITopic

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalMappingDecorator

from nti.externalization.singleton import SingletonDecorator

from nti.links.links import Link

from nti.property.property import Lazy

LINKS = StandardExternalFields.LINKS

@component.adapter(INote)
@interface.implementer(IExternalMappingDecorator)
class _NoteRequestDecorator(AbstractAuthenticatedRequestAwareDecorator):

    @Lazy
    def _acl_decoration(self):
        result = getattr(self.request, 'acl_decoration', True)
        return result

    def _predicate(self, context, result):
        return      self._acl_decoration \
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
class _MostRecentReplyDecorator(object):
    """
    Adds a link to get the most recent reply for a threadable context
    """
    
    __metaclass__ = SingletonDecorator
    
    def decorateExternalMapping(self, context, result):
		_links = result.setdefault(StandardExternalFields.LINKS, [])
		link = Link(context, rel='mostRecentReply', elements=('mostRecentReply',))
		interface.alsoProvides(link, ILocation)
		link.__name__ = ''
		link.__parent__ = context
		_links.append(link)
		
@component.adapter(ITopic)
@interface.implementer(IExternalMappingDecorator)
class _MostRecentReplyTopicDecorator(object):
    """
    Adds a link to get the most recent reply for a topic context
    """
    __metaclass__ = SingletonDecorator
    
    def decorateExternalMapping(self, context, result):
		_links = result.setdefault(StandardExternalFields.LINKS, [])
		link = Link(context, rel='mostRecentReply', elements=('mostRecentReply',))
		interface.alsoProvides(link, ILocation)
		link.__name__ = ''
		link.__parent__ = context
		_links.append(link)
    		