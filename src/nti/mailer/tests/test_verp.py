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

import fudge

from .._verp import principal_ids_from_verp
from .._verp import verp_from_recipients
from ..interfaces import EmailAddresablePrincipal


class TestVerp(unittest.TestCase):

	def test_pids_from_verp_email(self):
		fromaddr = b'no-reply+kaley.white%40nextthought.com.WBf3Ow@nextthought.com'

		pids = principal_ids_from_verp(fromaddr, default_key='alpha.nextthought.com')

		assert_that( pids, contains('kaley.white@nextthought.com'))

		# outdated values
		#fromaddr = b'no-reply+TGV4aVpvbGwuLWJOUlNZVS1ZV3FEanFvUi10dGRkLV82R01z@nextthought.com'
		#pids = principal_ids_from_verp(fromaddr, default_key='mathcounts.nextthought.com')
		#assert_that( pids, contains('LexiZoll'))

		pids = principal_ids_from_verp(fromaddr)
		assert_that( pids, is_(()))


	@fudge.patch('nti.mailer._verp.find_site_policy',
				 'nti.mailer._verp._get_signer_secret')
	def test_verp_from_recipients_in_site_uses_default_sender_realname(self, mock_find, mock_secret):
		class Policy(object):
			DEFAULT_EMAIL_SENDER = 'Janux <janux@ou.edu>'

		mock_find.is_callable().returns( (Policy, 'janux.ou.edu') )
		mock_secret.is_callable().returns( 'abc123' )

		prin = EmailAddresablePrincipal.__new__(EmailAddresablePrincipal)
		prin.email = 'foo@bar.com'
		prin.id = 'foo'

		addr = verp_from_recipients( 'no-reply@nextthought.com',
									 (prin,),
									 default_key='alpha.nextthought.com')

		assert_that( addr, is_('"Janux" <no-reply+foo.pRjtUA@nextthought.com>') )

		pids = principal_ids_from_verp(addr, default_key='alpha.nextthought.com')
		assert_that( pids, contains(prin.id))
