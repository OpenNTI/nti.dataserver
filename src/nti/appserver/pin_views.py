#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views relating to pinnable objects.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid.interfaces import IRequest

from pyramid.view import view_config

from zope import interface
from zope import component

from zope.location.interfaces import ILocation

from nti.app.renderers.caching import uncached_in_response

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.appserver.pyramid_authorization import has_permission

from nti.dataserver.authorization import ACT_UPDATE

from nti.dataserver.interfaces import IPinned
from nti.dataserver.interfaces import IPinnable

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalMappingDecorator

from nti.links.links import Link

LINKS = StandardExternalFields.LINKS


logger = __import__('logging').getLogger(__name__)


@interface.implementer(IExternalMappingDecorator)
@component.adapter(IPinnable, IRequest)
class PinnableLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _predicate(self, context, unused_result):
        result = self._is_authenticated \
             and has_permission(ACT_UPDATE, context, self.request)
        return result

    def _do_decorate_external(self, context, result):
        _links = result.setdefault(LINKS, [])
        rel = 'unpin' if IPinned.providedBy(context) else 'pin'
        link = Link(context,
                    rel=rel,
                    elements=(rel,))
        interface.alsoProvides(link, ILocation)
        link.__name__ = ''
        link.__parent__ = context
        _links.append(link)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=IPinnable,
             permission=ACT_UPDATE,
             request_method='POST',
             name='pin')
def _PinView(request):
    interface.alsoProvides(request.context, IPinned)
    return uncached_in_response(request.context)


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=IPinnable,
             permission=ACT_UPDATE,
             request_method='POST',
             name='unpin')
def _UnpinView(request):
    interface.noLongerProvides(request.context, IPinned)
    return uncached_in_response(request.context)
