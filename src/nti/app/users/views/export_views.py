#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid import httpexceptions as hexc

from pyramid.location import lineage

from pyramid.view import view_config
from pyramid.view import view_defaults

from requests.structures import CaseInsensitiveDict

import six

from zope import component

from zope.intid.interfaces import IIntIds

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.users import MessageFactory as _

from nti.app.users.views import username_search

from nti.common.string import is_true

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import IACE
from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IACLProvider
from nti.dataserver.interfaces import IDataserverFolder

from nti.dataserver.users.users import User

from nti.externalization import to_external_object
from nti.externalization.externalization import NonExternalizableObjectError

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.externalization.proxy import removeAllProxies

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.ntiids.oids import to_external_ntiid_oid

OID = StandardExternalFields.OID
CLASS = StandardExternalFields.CLASS
ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

INTID = 'IntId'
OBJECT = 'Object'
EXCEPTION = 'Exception'

logger = __import__('logging').getLogger(__name__)


@view_config(name='ObjectResolver')
@view_config(name='object_resolver')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='GET',
               context=IDataserverFolder,
               permission=nauth.ACT_NTI_ADMIN)
class ObjectResolverView(AbstractAuthenticatedView):

    def __call__(self):
        request = self.request
        ntiid = request.subpath[0] if request.subpath else ''
        if not ntiid:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u'Must specify a ntiid.'),
                             },
                             None)
        intids = component.getUtility(IIntIds)
        obj = find_object_with_ntiid(ntiid)
        if obj is None:
            raise hexc.HTTPNotFound()
        result = LocatedExternalDict()
        result['ACL'] = aces = []
        obj = removeAllProxies(obj)
        try:
            result[OBJECT] = to_external_object(obj)
        except NonExternalizableObjectError:
            result[OBJECT] = {
                CLASS: "NonExternalizableObject",
                OID: to_external_ntiid_oid(obj),
                OBJECT: "%s.%s" % (obj.__class__.__module__, obj.__class__.__name__)
            }
        result[INTID] = intids.queryId(obj)
        for resource in lineage(obj):
            acl = getattr(resource, '__acl__', None)
            if not acl:
                provider = IACLProvider(resource, None)
                acl = provider.__acl__ if provider is not None else None
            for ace in acl or ():
                if IACE.providedBy(ace):
                    aces.append(ace.to_external_string())
                else:
                    aces.append(str(ace))
            if aces:  # found something
                break
        return result


@view_config(name='ExportUsers')
@view_config(name='export_users')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='GET',
               context=IDataserverFolder,
               permission=nauth.ACT_NTI_ADMIN)
class ExportUsersView(AbstractAuthenticatedView):

    def __call__(self):
        request = self.request
        values = CaseInsensitiveDict(request.params)
        summary = is_true(values.get('summary'))
        term = values.get('term') or values.get('search')
        usernames = values.get('usernames') or values.get('username')
        if term:
            usernames = username_search(term)
        elif isinstance(usernames, six.string_types):
            usernames = set(usernames.split(','))
        result = LocatedExternalDict()
        items = result[ITEMS] = {}
        for username in usernames or ():
            user = User.get_user(username)
            if IUser.providedBy(user):
                username = user.username
                if summary:
                    items[username] = to_external_object(user, name='summary')
                else:
                    items[username] = to_external_object(user)
        result[TOTAL] = result[ITEM_COUNT] = len(items)
        return result
