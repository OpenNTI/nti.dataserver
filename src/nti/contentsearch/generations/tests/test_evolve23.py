#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import fudge

import nti.dataserver
import nti.contentsearch

from nti.dataserver import users
from nti.dataserver.contenttypes import Redaction
from nti.dataserver.utils.example_database_initializer import ExampleDatabaseInitializer

from nti.ntiids.ntiids import make_ntiid

from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch.constants import (redaction_, content_, replacementContent_, redactionExplanation_)

from nti.contentsearch.generations.evolve23 import evolve

from nti.dataserver.tests import mock_dataserver
from nti.dataserver.tests.mock_dataserver import  mock_db_trans, WithMockDS

from nti.deprecated import hides_warnings

from hamcrest import (assert_that, has_length, has_key)

class TestEvolve23(mock_dataserver.ConfiguringTestBase):
	set_up_packages = (nti.dataserver, nti.contentsearch)

	@hides_warnings
	@WithMockDS
	def test_evolve23(self):
		with mock_db_trans() as conn:
			context = fudge.Fake().has_attr(connection=conn)
			ExampleDatabaseInitializer(max_test_users=0, skip_passwords=True).install(context)

			jason = users.User.get_user(dataserver=mock_dataserver.current_mock_ds, username='jason.madden@nextthought.com')

			redaction = Redaction()
			redaction.selectedText = u'Fear'
			redaction.replacementContent = 'Ichigo'
			redaction.redactionExplanation = 'Have overcome it everytime I have been on the verge of death'
			redaction.creator = jason.username
			redaction.containerId = make_ntiid(nttype='bleach', specific='manga')
			redaction = jason.addContainedObject(redaction)

			rim = search_interfaces.IRepozeEntityIndexManager(jason)
			rim.index_content(redaction)

		with mock_db_trans() as conn:
			context = fudge.Fake().has_attr(connection=conn)
			evolve(context)

		with mock_db_trans() as conn:
			ds_folder = context.connection.root()['nti.dataserver']
			jason = ds_folder['users']['jason.madden@nextthought.com']
			rim = search_interfaces.IRepozeEntityIndexManager(jason)

			assert_that(rim, has_key(redaction_))
			catalog = rim[redaction_]
			assert_that(catalog, has_key(content_))
			assert_that(catalog, has_key(replacementContent_))
			assert_that(catalog, has_key(redactionExplanation_))

			hits = rim.search("fear")
			assert_that(hits, has_length(1))

			hits = rim.search("death")
			assert_that(hits, has_length(1))

			hits = rim.search("ichigo")
			assert_that(hits, has_length(1))
