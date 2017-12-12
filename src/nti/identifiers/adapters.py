#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from ZODB.interfaces import IConnection

from zope import component
from zope import interface

from zope.annotation import factory as an_factory

from nti.containers.dicts import CaseInsensitiveLastModifiedDict

from nti.dataserver.interfaces import IUser

from nti.identifiers.interfaces import IUserExternalIdentityContainer
from nti.identifiers.interfaces import IUserExternalIdentityValidator

logger = __import__('logging').getLogger(__name__)

EXTERNAL_IDENTITY_ANNOTATION_KEY = 'nti.identifiers.interfaces.IUserExternalIdentityContainer'


@component.adapter(IUser)
@interface.implementer(IUserExternalIdentityContainer)
class ExternalIdentityContainer(CaseInsensitiveLastModifiedDict):
    """
    Stores mappings of external_type -> external_id for a user.

    XXX: Do we want to site-scope this?
    """

    def add_external_mapping(self, external_type, external_id):
        self[external_type] = external_id

_ExternalIdentityContainerFactory = an_factory(ExternalIdentityContainer,
                                               EXTERNAL_IDENTITY_ANNOTATION_KEY)


def ExternalIdentityContainerFactory(obj):
    result = _ExternalIdentityContainerFactory(obj)
    if IConnection(result, None) is None:
        try:
            # pylint: disable=too-many-function-args
            IConnection(obj).add(result)
        except (TypeError, AttributeError):  # pragma: no cover
            pass
    return result


@component.adapter(IUser)
@interface.implementer(IUserExternalIdentityValidator)
class _UserExternalIdentityValidator(object):

    def __init__(self, context):
        self.user = self.context = context

    def is_valid(self, external_type, external_id):
        if external_type is None or external_id is None:
            return False
        result = False
        identity_container = IUserExternalIdentityContainer(self.user, None)
        if identity_container is not None:
            found_external_id = identity_container.get(external_type, '')
            result = found_external_id.lower() == external_id.lower()
        return result
