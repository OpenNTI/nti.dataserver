#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)
#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import unittest


from zope.dottedname import resolve as dottedname

class TestInterfaces(unittest.TestCase):

	def test_ifaces(self):
		dottedname.resolve('nti.appserver.invitations.interfaces')
