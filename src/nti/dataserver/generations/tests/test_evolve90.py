#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_not
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import same_instance

import fudge

from zope import component

from zope.annotation.interfaces import IAnnotations

from zope.intid.interfaces import IIntIds

from persistent.mapping import PersistentMapping

from nti.dataserver.generations.evolve90 import do_evolve

from nti.dataserver.users.digest import _DIGEST_META_KEY

from nti.dataserver.users.users import User

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.tests.mock_dataserver import mock_db_trans


class TestEvolve90(mock_dataserver.DataserverLayerTest):

    @mock_dataserver.WithMockDS
    def test_do_evolve(self):

        with mock_db_trans() as conn:
            context = fudge.Fake().has_attr(connection=conn)

            intids = component.getUtility(IIntIds)
            ichigo = User.create_user(username='ichigo@bleach.org')
            doc_id = intids.getId(ichigo)

            ds_folder = context.connection.root()['nti.dataserver']
            users = ds_folder['users']
            old_storage = PersistentMapping()
            IAnnotations(users)[_DIGEST_META_KEY] = old_storage
            old_storage[doc_id] = 'ichigo'

            do_evolve(context)

            assert_that(old_storage, has_length(0))
            new_storage = IAnnotations(users)[_DIGEST_META_KEY]
            assert_that(new_storage, has_length(1))
            assert_that(new_storage, has_entry(doc_id, 'ichigo'))

            assert_that(new_storage, is_not(same_instance(old_storage)))
