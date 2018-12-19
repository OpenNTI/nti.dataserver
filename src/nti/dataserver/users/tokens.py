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

from ZODB.interfaces import IConnection

from zope import component
from zope import interface

from zope.annotation.interfaces import IAnnotations

from zope.cachedescriptors.property import Lazy

from zope.container.contained import Contained
from zope.container.contained import NameChooser

from zope.container.interfaces import INameChooser

from nti.containers.containers import CaseInsensitiveCheckingLastModifiedBTreeContainer

from nti.dataserver.users.interfaces import IUserToken
from nti.dataserver.users.interfaces import IUserTokenContainer

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.ntiids.oids import to_external_ntiid_oid

from nti.property.property import alias

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import PermissiveSchemaConfigured as SchemaConfigured

USER_TOKEN_CONTAINER_KEY = 'tokens'


@interface.implementer(IUserToken)
class UserToken(SchemaConfigured,
                PersistentCreatedModDateTrackingObject,
                Contained):

    __external_can_create__ = True

    createDirectFieldProperties(IUserToken)

    mimeType = mime_type = "application/vnd.nextthought.usertoken"

    key = id = alias('__name__')

    def __init__(self, *args, **kwargs):
        SchemaConfigured.__init__(self, *args, **kwargs)
        PersistentCreatedModDateTrackingObject.__init__(self)

    @Lazy
    def ntiid(self):
        return to_external_ntiid_oid(self)


@interface.implementer(IUserTokenContainer)
class UserTokenContainer(CaseInsensitiveCheckingLastModifiedBTreeContainer,
                         SchemaConfigured):

    __external_can_create__ = False

    mimeType = mime_type = "application/vnd.nextthought.usertokencontainer"

    createDirectFieldProperties(IUserTokenContainer)

    creator = None

    def __init__(self, *args, **kwargs):
        CaseInsensitiveCheckingLastModifiedBTreeContainer.__init__(self)
        SchemaConfigured.__init__(self, *args, **kwargs)

    def get_all_tokens_by_scope(self, scope):
        """
        Finds all tokens described by the given scope, or None.
        """
        result = []
        for token in self.values():
            if token.scopes and scope in token.scopes:
                result.append(token)
        return result

    def store_token(self, token):
        if not getattr(token, 'id', None):
            token.id = INameChooser(self).chooseName(token.title, token)
        self[token.id] = token
        return token

    def remove_token(self, token):
        key = getattr(token, 'id', token)
        try:
            del self[key]
            result = True
        except KeyError:
            result = False
        return result

    @Lazy
    def ntiid(self):
        return to_external_ntiid_oid(self)


@component.adapter(IUserTokenContainer)
@interface.implementer(INameChooser)
class _UserTokenContainerNameChooser(NameChooser):
    """
    Creates UUID names for user tokens.
    """

    def generate_token_key(self):
        return str(uuid.uuid4().time_low)

    def chooseName(self, unused_name, obj):
        container = self.context
        result = None
        while result is not None and result in container:
            result = self.generate_token_key()
            if      result not in container \
                and self.checkName(result, obj):
                return result


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
