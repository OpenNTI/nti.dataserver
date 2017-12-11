#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import has_property

import unittest

from zope.dottedname import resolve as dottedname


class TestInterfaces(unittest.TestCase):

    def test_import_interfaces(self):
        dottedname.resolve('nti.processlifetime.interfaces')

    def test_events(self):
        from nti.processlifetime.interfaces import ApplicationProcessStarting
        event = ApplicationProcessStarting('config')
        assert_that(event,
                    has_property('xml_conf_machine', is_('config')))
