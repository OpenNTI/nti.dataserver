#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import unittest

from zope.dottedname import resolve as dottedname

from nti.invitations.tests import SharedConfiguringTestLayer


class TestInterfaces(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    def test_ifaces(self):
        dottedname.resolve('nti.invitations.interfaces')
