#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import fudge

import unittest

from hamcrest import assert_that
from hamcrest import calling
from hamcrest import raises

from nti.testing.matchers import verifiably_provides

from repoze.who.interfaces import IIdentifier
from repoze.who.interfaces import IAuthenticator
from repoze.who.interfaces import IChallenger
from repoze.who.interfaces import IMetadataProvider

from ..who_apifactory import _APIFactory
from ..who_apifactory import create_who_apifactory

class TestWhoAPIFactory(unittest.TestCase):

    def test_factory_creation_validates(self):
        bad_plugin = object()

        assert_that(calling(_APIFactory).with_args(identifiers=(object,)),
                    raises(TypeError))

    def test_factory_plugins_validate(self):
        factory = create_who_apifactory()

        for propname, iface in (('identifiers', IIdentifier),
                                ('authenticators', IAuthenticator),
                                ('challengers', IChallenger),
                                ('mdproviders', IMetadataProvider)):
            for _, plugin in getattr(factory, propname, ()):
                assert_that(plugin, verifiably_provides(iface))
            

    def test_factory_invocation_doesnt_validate(self):
        factory = create_who_apifactory()

        # Creating our factory validated all our plugins.
        # In the past, calling the factory also validated the plugins,
        # but that happens per request and can be expensive. Validate we don't do
        # that anymore.

        factory.identifiers = (('bad_plugin', object()), )

        # We can invoke our factory without blowing up.
        environ = {
            'REQUEST_METHOD': 'GET'
        }
        
        factory(environ)
