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

from nti.base.interfaces import INamedFile

from nti.contentfile.interfaces import IContentBaseFile

from nti.contentfolder.interfaces import IRootFolder
from nti.contentfolder.interfaces import ILockedFolder
from nti.contentfolder.interfaces import INamedContainer

from nti.contentfolder.utils import compute_path

from nti.dataserver.authorization import ACT_READ
from nti.dataserver.authorization import ACT_UPDATE
from nti.dataserver.authorization import ACT_DELETE

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalObjectDecorator

from nti.links.links import Link

LINKS = StandardExternalFields.LINKS

logger = __import__('logging').getLogger(__name__)


def _create_link(context, rel, name=None, method=None, params=None):
    elements = () if not name else (name,)
    link = Link(context, rel=rel, elements=elements,
                method=method, params=params)
    interface.alsoProvides(link, ILocation)
    link.__name__ = ''
    link.__parent__ = context
    return link


@component.adapter(INamedContainer)
@interface.implementer(IExternalObjectDecorator)
class _NamedFolderLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):

    @Lazy
    def _acl_decoration(self):
        return getattr(self.request, 'acl_decoration', True)

    def _predicate(self, unused_context, unused_result):
        return self._acl_decoration and self._is_authenticated

    def _do_decorate_external(self, context, result):
        request = self.request
        _links = result.setdefault(LINKS, [])

        # read based ops
        if has_permission(ACT_READ, context, request):
            for name, params in (('tree', {'flat': False}),
                                 ('contents', {'depth': 0})):
                _links.append(_create_link(context, name, "@@%s" % name,
                                           params=params))

            for name in ('export', 'search'):
                _links.append(_create_link(context, name, "@@%s" % name))

        # update based ops
        if has_permission(ACT_UPDATE, context, request):
            for name in ('mkdir', 'mkdirs', 'upload', 'import'):
                _links.append(_create_link(context, name, "@@%s" % name,
                                           method='POST'))

            if      not ILockedFolder.providedBy(context) \
                and not IRootFolder.providedBy(context):
                for name in ('move', 'clear', 'rename',):
                    _links.append(_create_link(context, name, "@@%s" % name,
                                               method='POST'))

        if      has_permission(ACT_DELETE, context, request) \
            and not ILockedFolder.providedBy(context):
            _links.append(_create_link(context, rel="delete", method='DELETE'))


@component.adapter(INamedFile)
@interface.implementer(IExternalObjectDecorator)
class _NamedFileLinkDecorator(AbstractAuthenticatedRequestAwareDecorator):

    @Lazy
    def _acl_decoration(self):
        return getattr(self.request, 'acl_decoration', True)

    def _predicate(self, context, unused_result):
        parent = getattr(context, '__parent__', None)
        return parent is not None \
            and self._acl_decoration \
            and self._is_authenticated \
            and INamedContainer.providedBy(parent)

    def _do_decorate_external(self, context, result):
        request = self.request
        _links = result.setdefault(LINKS, [])
        if      IContentBaseFile.providedBy(context) \
            and has_permission(ACT_READ, context, request):
            for name in ('external', 'associations',):
                _links.append(_create_link(context, name, "@@%s" % name))

        if has_permission(ACT_DELETE, context, request):
            _links.append(_create_link(context, rel="delete", method='DELETE'))

        if has_permission(ACT_UPDATE, context, request):
            for name in ('copy', 'move', 'rename'):
                _links.append(_create_link(context, name, "@@%s" % name,
                                           method='POST'))

            if IContentBaseFile.providedBy(context):
                _links.append(_create_link(context, rel="associate",
                                           name="@@associate", method='POST'))


@component.adapter(INamedFile)
@component.adapter(INamedContainer)
@interface.implementer(IExternalObjectDecorator)
class _ContextPathDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _do_decorate_external(self, context, result):
        path = result.get('path', None)
        parent = getattr(context, '__parent__', None)
        if not path and INamedContainer.providedBy(parent):
            result['path'] = compute_path(context)
