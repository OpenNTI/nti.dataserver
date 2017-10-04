#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import has_length
from hamcrest import assert_that

import time

import BTrees

from zope import component

from nti.invitations.index import create_invitations_catalog

from nti.invitations.interfaces import IInvitationsContainer

from nti.invitations.model import Invitation
from nti.invitations.model import InvitationsContainer

from nti.invitations.utils import get_invitations_ids
from nti.invitations.utils import get_expired_invitation_ids
from nti.invitations.utils import get_pending_invitation_ids
from nti.invitations.utils import get_random_invitation_code

from nti.invitations.tests import InvitationLayerTest

from nti.invitations.wref import InvitationWeakRef

from nti.wref.interfaces import IWeakRef


class TestUtils(InvitationLayerTest):

    def create_invitations(self):
        catalog = create_invitations_catalog(family=BTrees.family64)
        i1 = Invitation(code=u'bleach',
                        receiver=u'ichigo',
                        sender=u'aizen',
                        accepted=False,
                        site=u"dataserver2",
                        expiryTime=0.0)
        catalog.index_doc(1, i1)

        i2 = Invitation(code=u'bleach2',
                        receiver=u'ichigo',
                        sender=u'aizen',
                        accepted=False,
                        site=u"dataserver2",
                        expiryTime=time.time() - 2000)
        catalog.index_doc(2, i2)

        i3 = Invitation(code=u'bleach3',
                        receiver=u'ichigo',
                        sender=u'aizen',
                        accepted=False,
                        site=u"dataserver2",
                        expiryTime=time.time() + 1000)
        catalog.index_doc(3, i3)
        return catalog

    def test_get_invitations(self):
        catalog = self.create_invitations()
        invitations = get_invitations_ids(catalog=catalog)
        assert_that(invitations, has_length(3))

        invitations = get_invitations_ids(catalog=catalog)
        assert_that(invitations, has_length(3))

        invitations = get_invitations_ids(receivers="aizen", catalog=catalog)
        assert_that(invitations, has_length(0))

        invitations = get_invitations_ids(receivers="ichigo", catalog=catalog)
        assert_that(invitations, has_length(3))

        invitations = get_invitations_ids(senders="ichigo", catalog=catalog)
        assert_that(invitations, has_length(0))

        invitations = get_invitations_ids(senders="aizen", catalog=catalog)
        assert_that(invitations, has_length(3))

        invitations = get_invitations_ids(sites="xzy", catalog=catalog)
        assert_that(invitations, has_length(0))

        invitations = get_invitations_ids(sites="dataserver2", catalog=catalog)
        assert_that(invitations, has_length(3))

    def test_get_pending_invitations(self):
        catalog = self.create_invitations()

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

    def test_wref(self):
        container = InvitationsContainer()
        component.getGlobalSiteManager().registerUtility(container, IInvitationsContainer)
        invitation = Invitation(code=u'test_invitation',
                                receiver=u'ichigo',
                                sender=u'aizen',
                                accepted=True)
        container = component.getUtility(IInvitationsContainer)
        container.add(invitation)

        wref = InvitationWeakRef(invitation)
        assert_that(wref(), is_(invitation))
        dne_invitation = Invitation(code=u'dne',
                                    receiver=u'ichigo',
                                    sender=u'aizen',
                                    accepted=True)
        wref = InvitationWeakRef(dne_invitation)
        assert_that(wref(), none())
        wref2 = IWeakRef(dne_invitation)
        assert_that(wref2, is_(wref))

        component.getGlobalSiteManager().unregisterUtility(container,
                                                           IInvitationsContainer)
