#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid.interfaces import IRequest

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.container.contained import Contained
from zope.container.traversal import ITraversable

from zope.location.interfaces import LocationError
from zope.location.location import LocationProxy

from zope.schema.interfaces import IVocabulary

from zope.traversing.interfaces import IPathAdapter

from nti.site.interfaces import IHostPolicySiteManager

from nti.app.vocabularyregistry import VOCABULARIES

from nti.dataserver.authorization import ACT_READ
from nti.dataserver.authorization import ROLE_ADMIN

from nti.dataserver.authorization_acl import ace_allowing
from nti.dataserver.authorization_acl import acl_from_aces

from nti.dataserver.interfaces import ACE_DENY_ALL
from nti.dataserver.interfaces import ALL_PERMISSIONS
from nti.dataserver.interfaces import AUTHENTICATED_GROUP_NAME


@interface.implementer(IPathAdapter, ITraversable)
@component.adapter(IHostPolicySiteManager, IRequest)
class VocabulariesPathAdapter(Contained):

    __name__ = VOCABULARIES

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.__parent__ = context

    @Lazy
    def __acl__(self):
        aces = [ace_allowing(ROLE_ADMIN, ALL_PERMISSIONS, type(self)),
                ace_allowing(AUTHENTICATED_GROUP_NAME, ACT_READ, type(self)),
                ACE_DENY_ALL]
        result = acl_from_aces(aces)
        return result

    def traverse(self, name, furtherPath):
        vocab = component.queryUtility(IVocabulary, name=name)
        if vocab is None:
            raise LocationError(name)

        # If vocabulary is not persisted, delegate its parent to this adapter.
        return LocationProxy(vocab, self, name) if getattr(vocab, '__parent__', None) is None else vocab
