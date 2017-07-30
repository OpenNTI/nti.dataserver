#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys

from zope import component
from zope import interface

from zope.intid.interfaces import IIntIds

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.intids import MessageFactory as _

from nti.app.renderers.interfaces import INoHrefInResponse

from nti.dataserver import authorization as nauth
from nti.dataserver.interfaces import IDataserverFolder

from nti.externalization.interfaces import LocatedExternalDict


@view_config(name='IntIdInfo')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='GET',
               context=IDataserverFolder,
               permission=nauth.ACT_NTI_ADMIN)
class IntIdInfoView(AbstractAuthenticatedView):

    def __call__(self):
        intids = component.getUtility(IIntIds)
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        result['size'] = len(intids)
        result['minKey'] = intids.refs.minKey()
        result['maxKey'] = intids.refs.maxKey()
        result['attribute'] = getattr(intids, 'attribute', None)
        interface.alsoProvides(result, INoHrefInResponse)
        return result


@view_config(name='IntIdResolver')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='GET',
               context=IDataserverFolder,
               permission=nauth.ACT_NTI_ADMIN)
class IntIdResolverView(AbstractAuthenticatedView):

    def __call__(self):
        request = self.request
        uid = request.subpath[0] if request.subpath else ''
        if uid is None:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Must specify an intid.'),
                                 'code': 'MissingIntId',
                             },
                             None)
        try:
            uid = int(uid)
        except (ValueError, TypeError):
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Must specify a valid intid.'),
                                 'code': 'InvalidIntId',
                             },
                             None)
        intids = component.getUtility(IIntIds)
        try:
            result = intids.queryObject(uid)
        except Exception as e:
            exc_info = sys.exc_info()
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': str(e),
                                 'code': e.__class__.__name__,
                             },
                             exc_info[2])
        if result is None:
            raise_json_error(self.request,
                             hexc.HTTPNotFound,
                             {
                                 'message': _(u'Intid not found.'),
                                 'code': 'IntIdNotFound',
                             },
                             None)
        return result
