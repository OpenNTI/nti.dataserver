#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import BTrees

from .._repoze_index import create_catalog

from ..constants import (channel_, content_, keywords_, references_, note_, ntiid_,
						 last_modified_, containerId_, creator_, recipients_, sharedWith_,
						 highlight_, redaction_, replacementContent_, redactionExplanation_,
						 messageinfo_)

from . import ConfiguringTestBase

from hamcrest import (assert_that, has_key, is_)

class TestRepozeIndex(ConfiguringTestBase):

	def _test_common_catalog(self, catalog):
		assert_that(catalog.family, is_(BTrees.family64))
		assert_that(catalog, has_key(ntiid_))
		assert_that(catalog, has_key(creator_))
		assert_that(catalog, has_key(keywords_))
		assert_that(catalog, has_key(sharedWith_))
		assert_that(catalog, has_key(containerId_))
		assert_that(catalog, has_key(last_modified_))

	def test_notes_catalog(self):
		catalog = create_catalog(note_)
		self._test_common_catalog(catalog)
		assert_that(catalog, has_key(references_))
		assert_that(catalog, has_key(content_))

	def test_highlight_catalog(self):
		catalog = create_catalog(highlight_)
		self._test_common_catalog(catalog)
		assert_that(catalog, has_key(content_))

	def test_redaction_catalog(self):
		catalog = create_catalog(redaction_)
		self._test_common_catalog(catalog)
		assert_that(catalog, has_key(content_))
		assert_that(catalog, has_key(replacementContent_))
		assert_that(catalog, has_key(redactionExplanation_))

	def test_messageinfo_catalog(self):
		catalog = create_catalog(messageinfo_)
		self._test_common_catalog(catalog)
		assert_that(catalog, has_key(channel_))
		assert_that(catalog, has_key(recipients_))
		assert_that(catalog, has_key(references_))
		assert_that(catalog, has_key(content_))
