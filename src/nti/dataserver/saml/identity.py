#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id: identity.py 96465 2016-09-08 16:48:14Z bobby.hagen $
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.containers.containers import CheckingLastModifiedBTreeContainer

from nti.dataserver.interfaces import IUser

from zope import component
from zope import interface

from zope.annotation import factory as an_factory

from .interfaces import ISAMLIDPUserInfoBindings

SAML_IDP_USERINFO_BINDINGS_ANNOTATION_KEY = 'SAML_IDP_USERINFO_BINDINGS_ANNOTATION_KEY'

@component.adapter(IUser)
@interface.implementer(ISAMLIDPUserInfoBindings)
class SAMLIDPUserInfoBindings(CheckingLastModifiedBTreeContainer):
	pass

_SAMLIDPUserInfoBindingsFactory = an_factory(SAMLIDPUserInfoBindings,
											 SAML_IDP_USERINFO_BINDINGS_ANNOTATION_KEY)
