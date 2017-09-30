#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from zope.annotation import factory as an_factory

from nti.containers.containers import CheckingLastModifiedBTreeContainer

from nti.dataserver.interfaces import IUser

from nti.dataserver.saml.interfaces import SAML_IDP_USERINFO_BINDINGS_ANNOTATION_KEY

from nti.dataserver.saml.interfaces import ISAMLIDPUserInfoBindings

logger = __import__('logging').getLogger(__name__)


@component.adapter(IUser)
@interface.implementer(ISAMLIDPUserInfoBindings)
class SAMLIDPUserInfoBindings(CheckingLastModifiedBTreeContainer):
    pass
_SAMLIDPUserInfoBindingsFactory = an_factory(SAMLIDPUserInfoBindings,
                                             SAML_IDP_USERINFO_BINDINGS_ANNOTATION_KEY)
