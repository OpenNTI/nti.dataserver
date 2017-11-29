#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import assert_that
from hamcrest import has_property

from nti.dataserver.users.communities import Community

from nti.dataserver.users.interfaces import IFriendlyNamed

from nti.dataserver.utils import nti_update_community as nti_update

from nti.dataserver.tests import mock_dataserver

from nti.testing.base import ConfiguringTestBase


class TestUpdateCommunity(ConfiguringTestBase):

    set_up_packages = ('nti.dataserver',)

    def _create_comm(self, username=u'comm@nti.com'):
        ds = mock_dataserver.current_mock_ds
        comm = Community.create_community(ds, username=username)
        return comm

    @mock_dataserver.WithMockDSTrans
    def test_update_community(self):
        comms = []
        for x in range(1, 5):
            name = u'%s_comm@nti.com' % x
            comms.append(name)
            self._create_comm(name)

        comm = nti_update.update_community(u'1_comm@nti.com',
                                           u'foo',
                                           u'foo-alias')
        assert_that(comm, is_not(none()))
        profile = IFriendlyNamed(comm)
        assert_that(profile.realname, is_('foo'))
        assert_that(profile.alias, is_('foo-alias'))

        comm = nti_update.update_community(u'2_comm@nti.com',
                                           u'Аккредитация',
                                           u'преподавания')
        assert_that(comm, is_not(none()))
        profile = IFriendlyNamed(comm)
        assert_that(profile.realname, is_(u'Аккредитация'))
        assert_that(profile.alias, is_(u'преподавания'))

        comm = nti_update.update_community(u'3_comm@nti.com', u'Bleach',
                                           u'Ichigo', True, True)
        assert_that(comm, is_not(none()))
        profile = IFriendlyNamed(comm)
        assert_that(profile.realname, is_(u'Bleach'))
        assert_that(profile.alias, is_(u'Ichigo'))
        assert_that(comm, has_property('public', is_(True)))
        assert_that(comm, has_property('joinable', is_(True)))
