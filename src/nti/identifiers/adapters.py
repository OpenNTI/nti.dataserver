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

from zope.component.hooks import getSite

from nti.base._compat import text_

from nti.containers.dicts import CaseInsensitiveLastModifiedDict

from nti.coremetadata.interfaces import IUser

from nti.identifiers.interfaces import IUserExternalIdentityContainer
from nti.identifiers.interfaces import IUserExternalIdentityValidator
from nti.identifiers.interfaces import MultipleUserExternalIdentitySitesError

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import SchemaConfigured

EXTERNAL_IDENTITY_ANNOTATION_KEY = 'nti.identifiers.interfaces.IUserExternalIdentityContainer'

logger = __import__('logging').getLogger(__name__)


@component.adapter(IUser)
@interface.implementer(IUserExternalIdentityContainer)
class ExternalIdentityContainer(CaseInsensitiveLastModifiedDict, SchemaConfigured):
    """
    Stores mappings of external_type -> external_id for a user. Users are
    only allowed to be externally identified to one site.
    """
    createDirectFieldProperties(IUserExternalIdentityContainer)

    def _set_site_name(self):
        current_site = getattr(getSite(), '__name__', '')
        if current_site and current_site != 'dataserver2':
            # pylint: disable=access-member-before-definition
            if self.site_name and self.site_name != current_site:
                raise MultipleUserExternalIdentitySitesError()
            # pylint: disable=attribute-defined-outside-init
            self.site_name = text_(current_site)

    def add_external_mapping(self, external_type, external_id):
        self._set_site_name()
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
