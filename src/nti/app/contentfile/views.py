#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from requests.structures import CaseInsensitiveDict

from zope import lifecycleevent

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.contentfile import MessageFactory as _

from nti.app.contentfile.view_mixins import file_contraints

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.contentfile.interfaces import IContentBaseFile

from nti.dataserver import authorization as nauth

from nti.externalization import to_external_object

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.namedfile.interfaces import IFileConstrained

from nti.ntiids.ntiids import find_object_with_ntiid

OID = StandardExternalFields.OID
ITEMS = StandardExternalFields.ITEMS
NTIID = StandardExternalFields.NTIID
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

logger = __import__('logging').getLogger(__name__)


@view_config(context=IContentBaseFile)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               permission=nauth.ACT_READ,
               request_method='GET')
class ContentFileGetView(AbstractAuthenticatedView):

    def __call__(self):
        result = to_external_object(self.request.context)
        result.lastModified = self.request.context.lastModified
        return result


@view_config(context=IContentBaseFile)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               name='associations',
               permission=nauth.ACT_READ,
               request_method='GET')
class ContentFileAssociationsView(AbstractAuthenticatedView):

    def __call__(self):
        result = LocatedExternalDict()
        result[ITEMS] = items = []
        # pylint: disable=no-member
        if self.context.has_associations():
            items.extend(self.context.associations())
        result[ITEM_COUNT] = result[TOTAL] = len(items)
        return result


@view_config(context=IContentBaseFile)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               name='associate',
               permission=nauth.ACT_UPDATE,
               request_method='POST')
class ContentFileAssociateView(AbstractAuthenticatedView,
                               ModeledContentUploadRequestUtilsMixin):

    def readInput(self, value=None):
        data = super(ContentFileAssociateView, self).readInput(value)
        return CaseInsensitiveDict(data)

    def __call__(self):
        values = self.readInput()
        ntiid = values.get(NTIID) or values.get(OID) or values.get('target')
        if not ntiid:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Must provide a valid context id.'),
                                 'code': 'MustProvideValidContextID',
                             },
                             None)
        target = find_object_with_ntiid(ntiid)
        if target is None:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u"Cannot find target object."),
                                 'code': 'CannotFindTargetObject',
                             },
                             None)
        # pylint: disable=no-member
        if target is not self.context and target is not self.context.__parent__:
            self.context.add_association(target)
            lifecycleevent.modified(self.context)
        return hexc.HTTPNoContent()


@view_config(context=IFileConstrained)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               name='constrains',
               permission=nauth.ACT_READ,
               request_method='GET')
class FileConstrainsGetView(AbstractAuthenticatedView):

    def __call__(self):
        result = file_contraints(self.context, self.remoteUser)
        if result is None:
            return hexc.HTTPNotFound()
        return result
