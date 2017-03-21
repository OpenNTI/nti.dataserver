#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_length
from hamcrest import assert_that

import time
import unittest

import BTrees

from nti.invitations.index import create_invitations_catalog

from nti.invitations.model import Invitation

from nti.invitations.utils import get_expired_invitation_ids
from nti.invitations.utils import get_pending_invitation_ids
from nti.invitations.utils import get_random_invitation_code

from nti.invitations.tests import SharedConfiguringTestLayer


class TestUtils(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    def test_get_pending_invitations(self):
        catalog = create_invitations_catalog(family=BTrees.family64)
        i1 = Invitation(code='bleach',
                        receiver='ichigo',
                        sender='aizen',
                        accepted=False,
                        expiryTime=0.0)
        catalog.index_doc(1, i1)

        i2 = Invitation(code='bleach2',
                        receiver='ichigo',
                        sender='aizen',
                        accepted=False,
                        expiryTime=time.time() - 2000)
        catalog.index_doc(2, i2)

        i3 = Invitation(code='bleach3',
                        receiver='ichigo',
                        sender='aizen',
                        accepted=False,
                        expiryTime=time.time() + 1000)
        catalog.index_doc(3, i3)

        result = get_pending_invitation_ids("ichigo", catalog=catalog)
        assert_that(result, has_length(2))
        assert_that(sorted(result), is_([1, 3]))

        result = get_pending_invitation_ids("aizen", catalog=catalog)
        assert_that(result, has_length(0))

        result = get_expired_invitation_ids(catalog=catalog)
        assert_that(result, has_length(1))
        assert_that(sorted(result), is_([2]))

        result = get_expired_invitation_ids("ichigo", catalog=catalog)
        assert_that(result, has_length(1))
        assert_that(sorted(result), is_([2]))

        result = get_expired_invitation_ids("aizen", catalog=catalog)
        assert_that(result, has_length(0))

    def test_get_random_invitation_code(self):
        code = get_random_invitation_code()
        assert_that(code, has_length(12))
