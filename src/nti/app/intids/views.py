#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from requests.structures import CaseInsensitiveDict

from zope import component

from zope.intid.interfaces import IIntIds

from persistent.interfaces import IPersistent

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.dataserver import authorization as nauth
from nti.dataserver.interfaces import IDataserverFolder

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.intid.common import addIntId

from nti.ntiids.ntiids import find_object_with_ntiid

INTID = StandardExternalFields.INTID
NTIID = StandardExternalFields.NTIID


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
            raise hexc.HTTPUnprocessableEntity("Must specify a intid")

        try:
            uid = int(uid)
        except (ValueError, TypeError):
            raise hexc.HTTPUnprocessableEntity("Must specify a valid intid")

        intids = component.getUtility(IIntIds)
        result = intids.queryObject(uid)
        if result is None:
            raise hexc.HTTPNotFound()
        return result


@view_config(name='RegisterWithIntId')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=IDataserverFolder,
               permission=nauth.ACT_NTI_ADMIN)
class RegisterWithIntIdView(AbstractAuthenticatedView,
                            ModeledContentUploadRequestUtilsMixin):

    def readInput(self, value=None):
        result = super(RegisterWithIntIdView, self).readInput(value=value)
        return CaseInsensitiveDict(result)

    def __call__(self):
        values = self.readInput()
        ntiid = values.get(NTIID)
        if ntiid is None:
            raise hexc.HTTPUnprocessableEntity("Must specify an NTIID")
        obj = find_object_with_ntiid(ntiid)
        if obj is None:
            raise hexc.HTTPNotFound()
        if not IPersistent.providedBy(obj):
            raise hexc.HTTPUnprocessableEntity("Must be a persistent object")
        intids = component.getUtility(IIntIds)
        uid = intids.queryId(obj)
        if uid is None:
            addIntId(obj)
            uid = intids.queryId(obj)
        result = LocatedExternalDict()
        result[INTID] = uid
        result[NTIID] = ntiid
        return result
