#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=inherit-non-class

import uuid

from datetime import datetime

from persistent import Persistent

from persistent.list import PersistentList

from ZODB.interfaces import IConnection

from zope import component
from zope import interface

from zope.annotation.interfaces import IAnnotations

from zope.cachedescriptors.property import Lazy

from zope.component.hooks import getSite

from zope.container.contained import Contained

from zope.intid.interfaces import IIntIds

from nti.dataserver.users.interfaces import IUserToken
from nti.dataserver.users.interfaces import IUserTokenContainer

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.ntiids.oids import to_external_ntiid_oid

from nti.property.property import alias

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import PermissiveSchemaConfigured as SchemaConfigured

USER_TOKEN_CONTAINER_KEY = 'tokens'


def _generate_token(user):
    intids = component.getUtility(IIntIds)
    current_site = getSite()
    site_intid = intids.queryId(current_site)
    user_val = str(site_intid) if site_intid else ""
    user_intid = intids.queryId(user)
    if user_intid:
        user_val = "%s:%s" % (user_intid, user_val)
    return "%s:%s" % (str(uuid.uuid4().time_low), user_val)


@interface.implementer(IUserToken)
class UserToken(SchemaConfigured,
                PersistentCreatedModDateTrackingObject,
                Contained):

    __external_can_create__ = True

    createDirectFieldProperties(IUserToken)

    mimeType = mime_type = "application/vnd.nextthought.usertoken"

    value = alias('token')

    def __init__(self, *args, **kwargs):
        SchemaConfigured.__init__(self, *args, **kwargs)
        PersistentCreatedModDateTrackingObject.__init__(self)

    @Lazy
    def ntiid(self):
        return to_external_ntiid_oid(self)


@interface.implementer(IUserTokenContainer)
class UserTokenContainer(SchemaConfigured,
                         Persistent):

    __external_can_create__ = False

    mimeType = mime_type = "application/vnd.nextthought.usertokencontainer"

    createDirectFieldProperties(IUserTokenContainer)

    creator = None

    def __init__(self, *args, **kwargs):
        SchemaConfigured.__init__(self, *args, **kwargs)
        self.tokens = PersistentList()

    def get_all_tokens_by_scope(self, scope):
        """
        Finds all tokens described by the given scope, or an empty list.
        """
        result = []
        for token in self.tokens:
            if token.scopes and scope in token.scopes:
                result.append(token)
        return result

    def get_longest_living_token_by_scope(self, scope):
        """
        Return the longest living token for a scope, or None
        """
        tokens = self.get_all_tokens_by_scope(scope)
        if tokens:
            # No expiration date comes first
            tokens = sorted(tokens,
                            key=lambda x: (x.expiration_date or datetime.max))
            return tokens[0]

    def get_valid_tokens(self):
        """
        Return unexpired tokens.
        """
        now = datetime.utcnow()
        return [x for x in self.tokens if (x.expiration_date or datetime.max) > now]

    def clear(self):
        self.tokens = PersistentList()

    def store_token(self, token):
        if not token.token:
            user = self.__parent__
            token.token = _generate_token(user)
        self.tokens.append(token)
        return token

    def remove_token(self, token):
        try:
            self.tokens.remove(token)
            result = True
        except KeyError:
            result = False
        return result

    def __len__(self):
        return len(self.tokens)

    @Lazy
    def ntiid(self):
        return to_external_ntiid_oid(self)


def UserTokenContainerFactory(user):
    result = None
    annotations = IAnnotations(user)
    KEY = USER_TOKEN_CONTAINER_KEY
    try:
        result = annotations[KEY]
    except KeyError:
        result = UserTokenContainer()
        annotations[KEY] = result
        result.__name__ = KEY
        result.__parent__ = user
        IConnection(user).add(result)
    return result
