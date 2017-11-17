#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import six

from requests.structures import CaseInsensitiveDict

from zope import component

from zope.cachedescriptors.property import Lazy

from zope.intid.interfaces import IIntIds

from ZODB.POSException import POSError

from pyramid import httpexceptions as hexc

from pyramid.location import lineage

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.users import MessageFactory as _

from nti.app.users.views import username_search
from nti.app.users.views import parse_mime_types

from nti.chatserver.interfaces import IMessageInfo
from nti.chatserver.interfaces import IUserTranscriptStorage

from nti.common.string import is_true

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import IACE
from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IACLProvider
from nti.dataserver.interfaces import IDataserverFolder
from nti.dataserver.interfaces import IDeletedObjectPlaceholder

from nti.dataserver.users.users import User

from nti.dataserver.metadata.index import IX_CREATOR
from nti.dataserver.metadata.index import IX_MIMETYPE
from nti.dataserver.metadata.index import get_metadata_catalog

from nti.externalization.externalization import toExternalObject
from nti.externalization.externalization import NonExternalizableObjectError

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.externalization.proxy import removeAllProxies

from nti.mimetype.externalization import decorateMimeType

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.ntiids.oids import to_external_ntiid_oid

OID = StandardExternalFields.OID
CLASS = StandardExternalFields.CLASS
ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
MIMETYPE = StandardExternalFields.MIMETYPE
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

INTID = 'IntId'
OBJECT = 'Object'
MESSAGE = 'Message'
EXCEPTION = 'Exception'

transcript_mime_type = 'application/vnd.nextthought.transcript'
messageinfo_mime_type = 'application/vnd.nextthought.messageinfo'

logger = __import__('logging').getLogger(__name__)


def metadata_catalog():
    return get_metadata_catalog()


def get_user_objects(user, mime_types=()):
    catalog = metadata_catalog()
    intids = component.getUtility(IIntIds)

    result_ids = None
    created_ids = None
    mime_types_intids = None
    username = user.username
    process_transcripts = False

    if mime_types:
        mime_types = set(mime_types)
        process_transcripts = bool(
            transcript_mime_type in mime_types or messageinfo_mime_type in mime_types
        )
        if process_transcripts:
            mime_types.discard(transcript_mime_type)
            mime_types.discard(messageinfo_mime_type)

        if mime_types:
            mime_types = tuple(mime_types)
            mime_types_intids = catalog[IX_MIMETYPE].apply(
                {'any_of': mime_types}
            )
        else:
            created_ids = ()  # mark so we don't query the catalog
    else:
        process_transcripts = True

    if created_ids is None:
        created_ids = catalog[IX_CREATOR].apply({'any_of': (username,)})

    if mime_types_intids is None:
        result_ids = created_ids
    elif created_ids:
        result_ids = catalog.family.IF.intersection(created_ids,
                                                    mime_types_intids)

    for uid in result_ids or ():
        try:
            obj = intids.queryObject(uid)
            if     obj is None \
                or IUser.providedBy(obj) \
                or IDeletedObjectPlaceholder.providedBy(obj) \
                or (process_transcripts and IMessageInfo.providedBy(obj)):
                continue
            yield obj
        except (POSError, TypeError) as e:
            logger.debug("Error processing object %s(%s); %s",
                         type(obj), uid, e)

    if process_transcripts:
        storage = IUserTranscriptStorage(user)
        for transcript in storage.transcripts:
            yield transcript


@view_config(name='ExportUserObjects')
@view_config(name='export_user_objects')
@view_defaults(route_name='objects.generic.traversal',
               request_method='GET',
               context=IDataserverFolder,
               permission=nauth.ACT_NTI_ADMIN)
class ExportUserObjectsView(AbstractAuthenticatedView):

    @Lazy
    def _intids(self):
        return component.getUtility(IIntIds)

    def _externalize(self, obj, decorate=False):
        try:
            result = toExternalObject(obj, decorate=decorate)
            if MIMETYPE not in result:
                decorateMimeType(obj, result)
        except NonExternalizableObjectError:
            result = {
                CLASS: 'NonExternalizableObject',
                OID: to_external_ntiid_oid(obj),
                INTID: self._intids.queryId(obj),
                OBJECT: "%s.%s" % (obj.__class__.__module__, obj.__class__.__name__)
            }
        except Exception as e:
            logger.debug("Error processing object %s(%s); %s", type(obj), e)
            result = {
                MESSAGE: str(e),
                OBJECT: str(type(obj)),
                EXCEPTION: str(type(e)),
                CLASS: 'NonExternalizableObject'
            }
        return result

    def __call__(self):
        request = self.request
        values = CaseInsensitiveDict(request.params)
        term = values.get('term') or values.get('search')
        usernames = values.get('usernames') or values.get('username')
        if term:
            usernames = username_search(term)
        elif usernames:
            usernames = usernames.split(",")
        else:
            usernames = ()
        total = 0
        mime_types = values.get('accept') \
                  or values.get('mime_types') \
                  or values.get('mimeTypes') or ''
        mime_types = parse_mime_types(mime_types)
        result = LocatedExternalDict()
        items = result[ITEMS] = {}
        for username in usernames:
            user = User.get_user(username)
            if not IUser.providedBy(user):
                continue
            objects = items[username] = []
            for obj in get_user_objects(user, mime_types):
                ext_obj = self._externalize(obj)
                objects.append(ext_obj)
                total += 1
        result[TOTAL] = result[ITEM_COUNT] = total
        return result


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
            result[OBJECT] = toExternalObject(obj)
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
@view_config(name='export.users')
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
                    items[username] = toExternalObject(user, name='summary')
                else:
                    items[username] = toExternalObject(user)
        result[TOTAL] = result[ITEM_COUNT] = len(items)
        return result
