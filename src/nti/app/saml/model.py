#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.annotation import factory as an_factory

from nti.app.saml.interfaces import ISAMLIDPEntityBindings

from nti.containers.containers import CheckingLastModifiedBTreeContainer

from nti.dataserver.interfaces import IUser

SAML_IDP_BINDINGS_ANNOTATION_KEY = 'SAML_IDP_BINDINGS_ANNOTATION_KEY'


@component.adapter(IUser)
@interface.implementer(ISAMLIDPEntityBindings)
class SAMLIDPEntityBindings(CheckingLastModifiedBTreeContainer):
    pass

_SAMLIDEntityBindingsFactory = an_factory(SAMLIDPEntityBindings,
                                          SAML_IDP_BINDINGS_ANNOTATION_KEY)
