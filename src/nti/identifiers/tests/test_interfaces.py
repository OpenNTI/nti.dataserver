#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

import unittest

from zope.dottedname import resolve as dottedname

from nti.identifiers.tests import SharedConfiguringTestLayer


class TestInterfaces(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    def test_ifaces(self):
        dottedname.resolve('nti.identifiers.interfaces')
