#!/usr/bin/env python
# -*- coding: utf-8 -*-

#from __future__ import print_function, unicode_literals, absolute_import
#__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import unittest

from nti.contentsearch._blockio import BlockIO

from hamcrest import (assert_that, is_, has_length)

presidents = (	'George Washington, Independent',
				'John Adams, Federalist',
				'Thomas Jefferson, Democratic-Republican',
				'James Madison, Democratic-Republican',
				'James Monroe, Democratic-Republican',
				'John Quincy Adams, Democratic-Republican',
				'Andrew Jackson, Democratic',
				'Martin Van Buren, Democratic',
				'William Henry Harrison, Whig',
				'John Tyler, Whig',
				'James K. Polk, Democratic',
				'Zachary Taylor, Whig',
				'Millard Fillmore, Whig',
				)
class TestBlockIO(unittest.TestCase):

	def _test_blockIO(self, block_size=1024, source=presidents):
		lines = [x + '\n' for x in source]
		text = ''.join(lines)
		f = BlockIO(block_size)
		for line in lines[:-2]:
			f.write(line)
		f.writelines(lines[-2:])
		assert_that(f.getvalue(), is_(text))
	
		length = f.tell()
		assert_that(length, is_(380))
		
		f.seek(len(lines[0]))
		f.write(lines[1])
		f.seek(0)
		
		line = f.readline()
		assert_that(line, is_('George Washington, Independent\n'))
		assert_that(f.tell(), is_(31))
		
		line = f.readline()
		assert_that(line, is_('John Adams, Federalist\n'))
		
		f.seek(-len(line), 1)
		line2 = f.read(len(line))
		assert_that(line, is_(line2))
		
		f.seek(len(line2), 1)
		lines = f.readlines()
		assert_that(lines, has_length(11))
		
		line = lines[-1]
		f.seek(f.tell() - len(line))
		line2 = f.read()
		assert_that(line, is_(line2))
		
		assert_that(f.tell(), is_(380))
		
		f.truncate(length/2)
		f.seek(0, 2)
		assert_that(f.tell(), is_(190))

		f.truncate(0)
		assert_that(f, has_length(0))
		assert_that(f.len, is_(0))
		assert_that(f.pos, is_(0))
		
		f.close()
	
	def test_block_io(self):
		self._test_blockIO(2048)
		self._test_blockIO(1024)
		self._test_blockIO(512)
		self._test_blockIO(8)

if __name__ == '__main__':
	unittest.main()
	