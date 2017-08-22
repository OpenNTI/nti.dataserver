#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import none
from hamcrest import is_not
from hamcrest import assert_that
from hamcrest import has_property

import os
import unittest

from nti.app.authentication.saml_plugin import make_plugin
from nti.app.authentication.saml_plugin import _SAML2Plugin


class TestSAMLPlugin(unittest.TestCase):

    def test_plugin(self):
        path = os.path.join(os.path.dirname(__file__), "saml")
        plugin = make_plugin(path)
        assert_that(plugin, is_not(none()))

    def test_internals(self):
        if _SAML2Plugin is not object:
            assert_that(_SAML2Plugin, 
                        has_property('_pick_idp',  is_not(none())))
