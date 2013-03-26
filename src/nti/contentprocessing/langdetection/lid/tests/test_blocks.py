#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from .. import blocks

from . import ConfiguringTestBase

from hamcrest import (assert_that, is_)

class TestBlocks(ConfiguringTestBase):

	def test_unicode_blocks(self):
		for c in xrange(128):
			self.assert_block('Basic Latin', c)

		for c in xrange(0x80, 0x99):
			self.assert_block('Extended Latin', c)

		for c in xrange(0x100, 0x17F):
			self.assert_block('Extended Latin', c)

		for c in xrange(0x180, 0x24F):
			self.assert_block('Latin Extended-B', c)

		for c in xrange(0x250, 0x2B0):
			self.assert_block('Extended Latin', c)

		self.assert_block('Thai', 0xE00)
		self.assert_block('Thai', 0xE7F)
		self.assert_block('Lao', 0xE80)
		self.assert_block('Lao', 0x0EFF)
		self.assert_block('Tibetan', 0xF00)
		self.assert_block('Tibetan', 0xFFF)
		self.assert_block('Cyrillic', 0x421)

	def assert_block(self, name, c):
		c = unichr(c)
		block = blocks.unicode_block(c)
		assert_that(name, is_(block), '%s != %s for %r' % (name, block, c))
