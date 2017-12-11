#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that

import pickle
import unittest

import BTrees

import fudge

from zope import component

from zope.catalog.interfaces import ICatalog

from nti.invitations.index import CATALOG_NAME

from nti.invitations.index import ValidatingSite
from nti.invitations.index import ValidatingAccepted
from nti.invitations.index import ValidatingMimeType
from nti.invitations.index import create_invitations_catalog
from nti.invitations.index import install_invitations_catalog

from nti.invitations.model import Invitation


class TestIndex(unittest.TestCase):

    def test_pickle(self):
        for factory in (ValidatingAccepted,
                        ValidatingMimeType,
                        ValidatingSite):
            with self.assertRaises(TypeError):
                pickle.dumps(factory())

    def test_index(self):
        invitation = Invitation(code=u'bleach',
                                receiver=u'ichigo',
                                sender=u'aizen',
                                accepted=True)
        invitation.createdTime = invitation.lastModified = 100
        catalog = create_invitations_catalog(family=BTrees.family64)
        catalog.index_doc(1, invitation)
        query = {
            'accepted': {'any_of': (True,)},
            'sender': {'any_of': ('aizen',)},
            'receiver': {'any_of': ('ichigo',)}
        }
        ids = catalog.apply(query)
        assert_that(ids, is_not(none()))
        assert_that(ids, has_length(1))

    def test_install_publishing_catalog(self):
        intids = fudge.Fake().provides('register').has_attr(family=BTrees.family64)
        catalog = install_invitations_catalog(component, intids)
        assert_that(catalog, is_not(none()))
        assert_that(install_invitations_catalog(component, intids),
                    is_(catalog))
        component.getGlobalSiteManager().unregisterUtility(catalog, ICatalog,
                                                           CATALOG_NAME)
