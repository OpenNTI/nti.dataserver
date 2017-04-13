#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import none
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that

import unittest

import BTrees

from nti.invitations.index import create_invitations_catalog

from nti.invitations.model import Invitation

from nti.invitations.tests import SharedConfiguringTestLayer


class TestIndex(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    def test_index(self):
        invitation = Invitation(code='bleach',
                                receiver='ichigo',
                                sender='aizen',
                                accepted=True)
        invitation.createdTime = invitation.lastModified = 100
        catalog = create_invitations_catalog(family=BTrees.family64)
        catalog.index_doc(1, invitation)
        query = {
            'accepted': {'any_of':(True,)},
            'sender': {'any_of':('aizen',)},
            'receiver': {'any_of':('ichigo',)}
        }
        ids = catalog.apply(query)
        assert_that(ids, is_not(none()))
        assert_that(ids, has_length(1))
