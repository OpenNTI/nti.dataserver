#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import unittest
from hamcrest import assert_that
from hamcrest import is_
from hamcrest import contains

from .._verp import principal_ids_from_verp

class TestVerp(unittest.TestCase):

	def test_pids_from_verp_email(self):
		fromaddr = 'no-reply+a2FsZXkud2hpdGVAbmV4dHRob3VnaHQuY29tLjV4cXAyeTRoVURlMGVvOGtoXzM5SURZNlR4aw@nextthought.com'

		pids = principal_ids_from_verp(fromaddr, default_key='alpha.nextthought.com')
		assert_that( pids, contains('kaley.white@nextthought.com'))

		fromaddr = 'no-reply+TGV4aVpvbGwuLWJOUlNZVS1ZV3FEanFvUi10dGRkLV82R01z@nextthought.com'
		pids = principal_ids_from_verp(fromaddr, default_key='mathcounts.nextthought.com')
		assert_that( pids, contains('LexiZoll'))

		pids = principal_ids_from_verp(fromaddr)
		assert_that( pids, is_(()))
