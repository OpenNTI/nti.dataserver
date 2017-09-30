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

from nti.app.saml.interfaces import ISAMLIDPEntityBindings

from nti.containers.containers import CheckingLastModifiedBTreeContainer

from nti.dataserver.interfaces import IUser

KEY_SEPERATOR = u'|'

SAML_IDP_BINDINGS_ANNOTATION_KEY = 'SAML_IDP_BINDINGS_ANNOTATION_KEY'

logger = __import__('logging').getLogger(__name__)


@component.adapter(IUser)
@interface.implementer(ISAMLIDPEntityBindings)
class SAMLIDPEntityBindings(CheckingLastModifiedBTreeContainer):

    def _key_for_qualifiers(self, name_qualifier, sp_name_qualifier=None):
        if not name_qualifier:
            raise ValueError('Must provide a name_qualifier')

        if sp_name_qualifier:
            return name_qualifier + KEY_SEPERATOR + sp_name_qualifier
        return name_qualifier

    def _key(self, name_id, name_qualifier, sp_name_qualifier):
        nq = getattr(name_id, 'name_qualifier', name_qualifier)
        nq = nq if nq else name_qualifier
        spnq = getattr(name_id, 'sp_name_qualifier', sp_name_qualifier)
        spnq = spnq if spnq else sp_name_qualifier
        return self._key_for_qualifiers(nq, spnq)

    def binding(self, name_id, name_qualifier=None, sp_name_qualifier=None):
        key = self._key(name_id, name_qualifier, sp_name_qualifier)
        return self[key]

    def store_binding(self, name_id, name_qualifier=None, sp_name_qualifier=None):
        key = self._key(name_id, name_qualifier, sp_name_qualifier)
        self[key] = name_id

    def clear_binding(self, name_id, name_qualifier=None, sp_name_qualifier=None):
        key = self._key(name_id, name_qualifier, sp_name_qualifier)
        del self[key]


_SAMLIDEntityBindingsFactory = an_factory(SAMLIDPEntityBindings,
                                          SAML_IDP_BINDINGS_ANNOTATION_KEY)
