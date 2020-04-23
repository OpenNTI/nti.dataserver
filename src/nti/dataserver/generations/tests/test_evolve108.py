#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division

__docformat__ = "restructuredtext en"

import fudge

from hamcrest import assert_that
from hamcrest import contains_inanyorder
from hamcrest import has_length
from hamcrest import none
from hamcrest import not_

from zope.securitypolicy.interfaces import IPrincipalRoleManager

from zope.securitypolicy.settings import Allow

from nti.dataserver.authorization import ROLE_ADMIN

from nti.dataserver.users.users import User

from nti.dataserver.generations.evolve108 import do_evolve

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.tests.mock_dataserver import mock_db_trans


class TestEvolve108(mock_dataserver.DataserverLayerTest):

    @mock_dataserver.WithMockDS
    def test_do_evolve(self):

        with mock_db_trans(self.ds) as conn:
            context = fudge.Fake().has_attr(connection=conn)

            admin_1 = User.create_user(username='nti1@nextthought.com')
            admin_2 = User.create_user(username='nti2@nextthought.com')

            User.create_user(username='user1@something.org')
            User.create_user(username='user2@somethingelse.org')

            # Make sure we get an appropriate role manager for the ds folder
            ds_folder = conn.root()['nti.dataserver']
            role_manager = IPrincipalRoleManager(ds_folder, None)
            assert_that(role_manager, not_(none()))

            # Make sure all the nextthought.com users have admin role there
            admin_principals = role_manager.getPrincipalsForRole(ROLE_ADMIN.id)
            assert_that(admin_principals, has_length(1))

            do_evolve(context)

            # Make sure we get an appropriate role manager for the ds folder
            ds_folder = conn.root()['nti.dataserver']
            role_manager = IPrincipalRoleManager(ds_folder, None)
            assert_that(role_manager, not_(none()))

            # Make sure all the nextthought.com users have admin role there
            admin_principals = role_manager.getPrincipalsForRole(ROLE_ADMIN.id)
            assert_that(admin_principals, contains_inanyorder(('admin@nextthought.com', Allow),
                                                              (admin_1.username, Allow),
                                                              (admin_2.username, Allow)))
