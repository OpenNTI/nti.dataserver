#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import raises
from hamcrest import calling
from hamcrest import assert_that
from hamcrest import greater_than
from hamcrest import has_property

import unittest

class TestLockerPatch(unittest.TestCase):

	def test_patch_storage_error(self):
		from relstorage.adapters.locker import MySQLLocker

		from .. import relstorage_locker_patch_on_import
		relstorage_locker_patch_on_import.patch()

		locker = MySQLLocker.__new__(MySQLLocker)
		locker.commit_lock_timeout = 0

		class Cursor(object):
			def execute(self, *args):
				pass

			def fetchone(self):
				return [0]

		assert_that( calling(locker.hold_commit_lock).with_args(Cursor()),
					 raises(relstorage_locker_patch_on_import.UnableToAcquireCommitLock) )

	def test_patch_duration(self):
		from relstorage.adapters.locker import MySQLLocker

		from .. import relstorage_locker_patch_on_import
		relstorage_locker_patch_on_import.patch()

		locker = MySQLLocker.__new__(MySQLLocker)
		locker.commit_lock_timeout = 0

		class Cursor(object):
			def execute(self, *args):
				pass

			def fetchone(self):
				return [1]

		locker.hold_commit_lock(Cursor())

		assert_that(locker, has_property('locked_at', greater_than(0)))

		locker.locked_at = locker.locked_at - 500

		locker.release_commit_lock(Cursor())

		assert_that(locker, has_property('locked_at', 0))
