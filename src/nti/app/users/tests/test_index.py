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

import unittest

import BTrees

import fudge

from zope import component

from zope.catalog.interfaces import ICatalog

from nti.app.users.index import CATALOG_NAME

from nti.app.users.index import create_context_lastseen_catalog
from nti.app.users.index import install_context_lastseen_catalog

from nti.app.users.model import ContextLastSeenRecord


class TestIndex(unittest.TestCase):

    def test_index(self):
        record = ContextLastSeenRecord(username=u'bleach',
                                       context=u'aizen',
                                       timestamp=1)
        catalog = create_context_lastseen_catalog(family=BTrees.family64)
        catalog.index_doc(1, record)
        query = {
            'timestamp': {'any_of': (1,)},
            'username': {'any_of': ('bleach',)},
            'context': {'any_of': ('aizen',)}
        }
        ids = catalog.apply(query)
        assert_that(ids, is_not(none()))
        assert_that(ids, has_length(1))

    def test_install_catalog(self):
        intids = fudge.Fake().provides('register').has_attr(family=BTrees.family64)
        catalog = install_context_lastseen_catalog(component, intids)
        assert_that(catalog, is_not(none()))
        assert_that(install_context_lastseen_catalog(component, intids),
                    is_(catalog))
        component.getGlobalSiteManager().unregisterUtility(catalog, ICatalog,
                                                           CATALOG_NAME)
